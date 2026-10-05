from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product
from app.models.reviews import Review


async def update_product_rating(product: Product, db: AsyncSession) -> None:
    """Функция перерасчета рейтинга товара."""
    av_rating = (
        await db.execute(
            select(func.avg(Review.grade))
            .where(Review.product_id == product.id, Review.is_active == True)
        )
    ).scalar()
    product.rating = av_rating or 0.0
