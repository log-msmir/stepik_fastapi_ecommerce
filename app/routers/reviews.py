from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ReviewRead, ReviewCreate
from app.db_depends import get_async_db
from app.models.reviews import Review
from app.models.users import User
from app.models.products import Product
from app.auth import get_current_buyer, is_review_author_or_admin
from app.service import update_product_rating


router = APIRouter(
    tags=['reviews']
)


@router.get(
        '/reviews',
        response_model=list[ReviewRead]
)
async def get_reviews(
    db: AsyncSession = Depends(get_async_db)
):
    """Получить список всех активных отзывов."""
    return (
        await db.scalars(
            select(Review)
            .where(Review.is_active == True)
        )
    ).all()


@router.post(
        '/reviews',
        response_model=ReviewRead,
        status_code=status.HTTP_201_CREATED
)
async def create_review(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_buyer)
):
    """Опубликовать новый отзыв о продукте."""
    product = (
        await db.scalars(
            select(Product)
            .where(Product.id == review.product_id)
            .where(Product.is_active == True)
        )
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Product not found or inactive'
        )
    new_review = Review(
        **review.model_dump(exclude_unset=True),
        user_id=current_user.id
    )
    db.add(new_review)
    try:
        await db.flush()
        await update_product_rating(product=product, db=db)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Возникла ошибка при сохранении ревью, попробуйте позже.'
        )
    
    await db.refresh(new_review)
    return new_review


@router.get(
    '/products/{product_id}/reviews',
    response_model=list[ReviewRead]
)
async def get_reviews_by_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Получить список отзывов о продукте."""
    product = (
        await db.scalars(
            select(Product)
            .where(Product.id == product_id, Product.is_active == True)
        )
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive'
        )

    return (
        await db.scalars(
            select(Review)
            .where(Review.product_id == product_id, Review.is_active == True)
        )
    )


@router.delete(
    '/reviews/{review_id}',
    response_model=dict
)
async def delete_review(
    review: Review = Depends(is_review_author_or_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Удалить отзыв о продукте."""
    product = (
        await db.scalars(
            select(Product)
            .where(Product.id == review.product_id, Product.is_active == True)
        )
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found or inactive'
        )
    try:
        review.is_active = False
        await db.flush()
        await update_product_rating(product=product, db=db)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Возникла ошибка при удалении ревью, попробуйте позже.'
        )
    return {"message": "Review deleted"}
