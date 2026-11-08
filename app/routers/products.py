from typing import Annotated
from pathlib import Path
import uuid

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query,
    UploadFile, File
)
from sqlalchemy import select, and_, func, desc, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product
from app.models.categories import Category
from app.models.users import User
from app.schemas import (
    ProductCreate, ProductRead, ProductList, Pagination, ProductsFilterParams,
    ProductsOrderingParams, ProductSearchParams
)
from app.db_depends import get_async_db
from app.auth import get_current_seller
from app.filters import (
    get_product_filters, get_product_ordering, get_products_search
) 

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 097 152 байт


router = APIRouter(
    prefix='/products',
    tags=['products'],
)

pagination_params = Annotated[Pagination, Query()]
products_filters_params = Annotated[ProductsFilterParams, Query()]
products_ordering_params = Annotated[ProductsOrderingParams, Query()]
products_search_params = Annotated[ProductSearchParams, Query()]


async def save_product_image(file: UploadFile) -> str:
    """
    Сохраняет изображение товара и возвращает относительный URL.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only JPG, PNG or WebP images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image is too large")

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f"/media/products/{file_name}"


def remove_product_image(url: str | None) -> None:
    """
    Удаляет файл изображения, если он существует.
    """
    if not url:
        return
    relative_path = url.lstrip("/")
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()


@router.get("/", response_model=ProductList)
async def get_all_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int | None = Query(None, description="ID категории для фильтрации"),
    search: str | None = Query(None, min_length=1, description="Поиск по названию/описанию"),
    min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
    max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
    in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
    seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
    db: AsyncSession = Depends(get_async_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [Product.is_active.is_(True)]

    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)
    if in_stock is not None:
        filters.append(Product.stock > 0 if in_stock else Product.stock == 0)
    if seller_id is not None:
        filters.append(Product.seller_id == seller_id)

    # Базовый запрос total
    total_stmt = select(func.count()).select_from(Product).where(*filters)

    rank_col = None
    if search:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(Product.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(Product.tsv, ts_query).label("rank")
            # total с учётом полнотекстового фильтра
            total_stmt = select(func.count()).select_from(Product).where(*filters)

    total = await db.scalar(total_stmt) or 0

    # Основной запрос (если есть поиск — добавим ранг в выборку и сортировку)
    if rank_col is not None:
        products_stmt = (
            select(Product, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), Product.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)
        rows = result.all()
        items = [row[0] for row in rows]    # сами объекты
        # при желании можно вернуть ранг в ответе
        # ranks = [row.rank for row in rows]
    else:
        products_stmt = (
            select(Product)
            .where(*filters)
            .order_by(Product.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.scalars(products_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post(
        "/",
        response_model=ProductRead,
        status_code=status.HTTP_201_CREATED
)
async def create_product(
        product: ProductCreate = Depends(ProductCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_seller)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """

    category_result = await db.scalars(
        select(Category).where(Category.id == product.category_id,
                                    Category.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found or inactive")

    # Сохранение изображения (если есть)
    image_url = await save_product_image(image) if image else None

    # Создание товара
    db_product = Product(
        **product.model_dump(),
        seller_id=current_user.id,
        image_url=image_url,
    )

    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


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


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
        product_id: int,
        product: ProductCreate = Depends(ProductCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_seller)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(
        select(Product).where(Product.id == product_id, Product.is_active == True)
    )
    db_product = result.first()
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    if db_product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )
    category_result = await db.scalars(
        select(Category).where(Category.id == product.category_id,
                                    Category.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found or inactive")

    await db.execute(
        update(Product).where(Product.id == product_id).values(**product.model_dump())
    )

    if image:
        remove_product_image(db_product.image_url)
        db_product.image_url = await save_product_image(image)

    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{product_id}", response_model=ProductRead)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(
        select(Product).where(Product.id == product_id, Product.is_active == True)
    )
    product = result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")

    remove_product_image(product.image_url)

    await db.execute(
        update(Product).where(Product.id == product_id).values(image_url=None,
                                                                         is_active=False)
    )

    await db.commit()
    await db.refresh(product)
    return product
