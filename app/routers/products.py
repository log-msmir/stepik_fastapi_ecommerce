from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product
from app.models.categories import Category
from app.models.users import User
from app.schemas import ProductCreate, ProductRead
from app.db_depends import get_async_db
from app.auth import get_current_seller


router = APIRouter(
    prefix='/products',
    tags=['products'],
)


@router.get('/', response_model=list[ProductRead])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    return (await db.scalars(
        select(Product).where(Product.is_active == True)
    )).all()


@router.post(
        '/',
        response_model=ProductRead,
        status_code=status.HTTP_201_CREATED
)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Создаёт новый товар.
    """
    category = (await db.scalars(
        select(Category)
        .where(
            and_(
                Category.id == product.category_id,
                Category.is_active == True)
        )
    )).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found or inactive'
        )
    new_product = Product(**product.model_dump(), seller_id=current_user.id)
    try:
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Возникла ошибка при создании товара.'
        )
    return new_product


@router.get('/category/{category_id}', response_model=list[ProductRead])
async def get_products_by_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    category = (await db.scalars(
        select(Category)
        .options(selectinload(Category.products))
        .where(
            and_(
                Category.id == category_id,
                Category.is_active == True)
        )
    )).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found or inactive'
        )
    return category.products


@router.get('/{product_id}', response_model=ProductRead)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product = (await db.scalars(
        select(Product)
        .where(
            and_(
                Product.id == product_id,
                Product.is_active == True
            )
        )
    )).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive'
        )
    return product


@router.put('/{product_id}', response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_seller),
):
    """
    Обновляет товар по его ID.
    """
    product = (await db.scalars(
        select(Product)
        .where(
            and_(
                Product.id == product_id,
                Product.is_active == True
            )
        )
    )).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive'
        )
    category = (await db.scalars(
        select(Category)
        .where(Category.id == product.category_id)
        .where(Category.is_active == True)
        )
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found or inactive'
        )
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You can only update your own products'
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Возникла ошибка при обновлении товара.'
        )
    return product


@router.delete('/{product_id}', response_model=dict)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_seller),
) -> dict:
    """
    Удаляет товар по его ID.
    """
    product = (await db.scalars(
        select(Product)
        .where(
            and_(
                Product.id == product_id,
                Product.is_active == True
            )
        )
    )).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive'
        )
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You can only delete your own products'
        )
    product.is_active = False
    await db.commit()
    return {'status': 'success', 'message': 'Product marked as inactive'}
