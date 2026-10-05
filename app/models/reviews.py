from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates

from app.database import Base


class Review(Base):
    """Модель отзыва."""

    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id')
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('products.id')
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    comment_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )
    grade: Mapped[int] = mapped_column(
        Integer
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    user: Mapped['User'] = relationship(
        'User',
        back_populates='reviews'
    )
    product: Mapped['Product'] = relationship(
        'Product',
        back_populates='reviews'
    )

    @validates('grade')
    def validate_grade(self, field, value):
        if 1 > value or value > 5:
            raise ValueError(
                f'Введено некорректное значение оценки: {value}. '
                'Укажите оценку в диапазоне от 1 до 5.'
            )
        return value
