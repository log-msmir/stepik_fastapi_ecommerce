from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db
from app.models.categories import Category
from app.schemas import CategoryRead, CategoryCreate
from app.auth import get_current_admin


router = APIRouter(
    prefix='/categories',
    tags=['categories'],
)


@router.get('/', response_model=list[CategoryRead])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных категорий.
    """
    return (
        await db.scalars(select(Category).where(Category.is_active==True))
    ).all()


@router.post(
        '/',
        response_model=CategoryRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(get_current_admin)]
)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Создаёт новую категорию.
    """
    if category.parent_id is not None:
        stmt = select(Category).where(Category.id == category.parent_id,
                                           Category.is_active == True)
        result = await db.scalars(stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(
                status_code=400,
                detail='Parent category not found'
            )

    db_category = Category(**category.model_dump())
    db.add(db_category)
    await db.commit()
    return db_category


@router.put(
        '/{category_id}',
        response_model=CategoryRead,
        dependencies=[Depends(get_current_admin)]
)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID.
    """
    db_category = (
        await db.scalars(
            select(Category)
            .where(Category.id == category_id, Category.is_active == True)
        )
    ).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found'
        )

    if category.parent_id is not None:
        parent = (
            await db.scalars(
                select(Category)
                .where(
                    Category.id == category.parent_id,
                    Category.is_active == True
                )
            )
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Parent category not found'
            )
        if parent.id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Category cannot be its own parent'
            )

    update_data = category.model_dump(exclude_unset=True)
    await db.execute(
        update(Category)
        .where(Category.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    return db_category


@router.delete(
        '/{category_id}',
        response_model=CategoryRead,
        dependencies=[Depends(get_current_admin)]
)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Мягкое удаление категории по её ID, устанавливая is_active = False.
    """
    db_category = (
        await db.scalars(
            select(Category)
            .where(Category.id == category_id, Category.is_active == True)
        )
    ).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found'
        )

    await db.execute(
        update(Category)
        .where(Category.id == category_id)
        .values(is_active=False)
    )
    await db.commit()
    return db_category
