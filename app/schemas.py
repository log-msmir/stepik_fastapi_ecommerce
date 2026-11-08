from typing import Literal, Annotated
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from fastapi import Form

from pydantic import BaseModel, Field, ConfigDict, EmailStr, model_validator

from app.models import Product


class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description='Название категории (3-50 символов)'
    )
    parent_id: int | None = Field(
        None,
        description='ID родительской категории, если есть'
    )


class CategoryRead(BaseModel):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: int = Field(
        ...,
        description='Уникальный идентификатор категории'
    )
    name: str = Field(
        ...,
        description='Название категории'
    )
    parent_id: int | None = Field(
        None,
        description='ID родительской категории, если есть'
    )
    is_active: bool = Field(
        ...,
        description='Активность категории'
    )

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название товара (3-100 символов)"
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Описание товара (до 500 символов)"
    )
    price: Decimal = Field(
        gt=0,
        description="Цена товара (больше 0)",
        decimal_places=2
    )
    stock: int = Field(
        ...,
        ge=0,
        description="Количество товара на складе (0 или больше)"
    )
    category_id: int = Field(
        ...,
        description="ID категории, к которой относится товар"
    )

    @classmethod
    def as_form(
            cls,
            name: Annotated[str, Form(...)],
            price: Annotated[Decimal, Form(...)],
            stock: Annotated[int, Form(...)],
            category_id: Annotated[int, Form(...)],
            description: Annotated[str | None, Form()] = None,
    ) -> "ProductCreate":
        return cls(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
        )


class ProductRead(BaseModel):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    id: int = Field(
        ...,
        description='Уникальный идентификатор товара'
    )
    name: str = Field(
        ...,
        description='Название товара'
    )
    description: str | None = Field(
        None,
        description='Описание товара'
    )
    price: Decimal = Field(
        ...,
        description='Цена товара в рублях',
        gt=0,
        decimal_places=2
    )
    image_url: str | None = Field(
        None,
        description='URL изображения товара'
    )
    stock: int = Field(
        ...,
        description='Количество товара на складе'
    )
    rating: float = Field(
        ...,
        description='Рейтинг товара'
    )
    category_id: int = Field(
        ...,
        description='ID категории'
    )
    is_active: bool = Field(
        ...,
        description='Активность товара'
    )

    model_config = ConfigDict(from_attributes=True)


class ProductList(BaseModel):
    """
    Список пагинации для товаров.
    """
    items: list[ProductRead] = Field(
        description="Товары для текущей страницы"
    )
    total: int = Field(
        ge=0,
        description="Общее количество товаров"
    )
    page: int = Field(
        ge=1,
        description="Номер текущей страницы"
    )
    page_size: int = Field(
        ge=1,
        description="Количество элементов на странице"
    )
    
    model_config = ConfigDict(from_attributes=True)  # Для чтения из ORM-объектов


class UserCreate(BaseModel):
    """Схема создания пользователя."""
    email: EmailStr = Field(
        description='Email пользователя'
    )
    password: str = Field(
        min_length=8,
        description='Пароль (минимум 8 символов)'
    )
    role: str = Field(
        default='buyer',
        pattern='^(buyer|seller)$',
        description='Роль: "buyer" или "seller"'
    )


class UserRead(BaseModel):
    """Схема чтения пользователя."""
    id: int = Field(
        description='Уникальный идентификатор пользователя'
    )
    email: EmailStr = Field(
        description='Email пользователя'
    )
    is_active: bool = Field(
        description='Статус пользователя'
    )
    role: str = Field(
        description='Роль пользователя'
    )

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ReviewCreate(BaseModel):
    """Схема создания отзыва."""
    product_id: int = Field(
        ...,
        description='Идентификатор продукта'
    )
    comment: str | None = Field(
        None,
        description='Текст отзыва'
    )
    grade: int = Field(
        ...,
        description='Оценка от 1 до 5',
        ge=1,
        le=5
    )
    

class ReviewRead(ReviewCreate):
    """Схема чтения отзыва."""
    id: int = Field(
        ...,
        description='Идентификатор отзыва'
    )
    is_active: bool = Field(
        description='Статус отзыва'
    )
    comment_date: datetime = Field(
        ...,
        description='Дата и время отзыва'
    )
    user_id: int = Field(
        ...,
        description='Идентификатор пользователя'
    )

    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    """Схема для работы с пагинацией."""

    page: int = Field(
        ge=1,
        default=1,
        description='Номер страницы для пагинации'
    )
    page_size: int = Field(
        ge=1,
        le=100,
        default=20,
        description='Количество товаров на одной странице'
    )


class ProductsFilterParams(BaseModel):
    """Запрос для фильтрации товаров."""

    category_id: int | None = Field(
        None,
        description='ID категории для фильтрации'
    )
    min_price: float | None = Field(
        None,
        ge=0,
        description='Минимальная цена товара'
    )
    max_price: float | None = Field(
        None,
        ge=0,
        description='Максимальная цена товара'
    )
    in_stock: bool | None = Field(
        None,
        description='true — товары в наличии, false — только без остатка'
    )
    seller_id: int | None = Field(
        None,
        description='ID продавца для фильтрации'
    )
    created_after: date | None = Field(
        None,
        ge=datetime(year=2026, month=10, day=6).date(),
        description='Товары с датой создания после числа. Формат: YYYY-MM-DD'
    )
    created_before: date | None = Field(
        None,
        description='Товары с датой создания не позже числа. Формат: YYYY-MM-DD'
    )

    @model_validator(mode='after')  # after - сначала данные пройдут валидацию схемой, Вернет 422 ошибку
    def check_price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError('Min_price не может быть больше max_price')
        return self

    @model_validator(mode='after')
    def check_date_range(self):
        if (
            self.created_after is not None
            and self.created_before is not None
            and self.created_after > self.created_before
        ):
            raise ValueError(
                'created_after не может быть больше created_before'
            )
        return self


class ProductsOrderingParams(BaseModel):
    """Запрос для формирования сортировки по товарам."""

    sort: list[Literal['created_at', '-created_at']] | None = Field(
        None,
        pattern=r"^-?created_at$",
        description=(
            'Сортировка по возрастанию (created_at) / убыванию (-created_at)'
        )
    )


class ProductSearchParams(BaseModel):
    """Запрос для формирования """

    search: str | None = Field(
        None,
        min_length=1,
        description="Поиск по названию товара"
     )


class CartItemBase(BaseModel):
    """Базовая схема корзины."""
    product_id: int = Field(description="ID товара")
    quantity: int = Field(ge=1, description="Количество товара")


class CartItemCreate(CartItemBase):
    """Модель для добавления нового товара в корзину."""
    pass

class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине."""
    quantity: int = Field(..., ge=1, description="Новое количество товара")


class CartItem(BaseModel):
    """Товар в корзине с данными продукта."""
    id: int = Field(..., description="ID позиции корзины")
    quantity: int = Field(..., ge=1, description="Количество товара")
    product: ProductRead = Field(..., description="Информация о товаре")

    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    """Полная информация о корзине пользователя."""
    user_id: int = Field(..., description="ID пользователя")
    items: list[CartItem] = Field(default_factory=list, description="Содержимое корзины")
    total_quantity: int = Field(..., ge=0, description="Общее количество товаров")
    total_price: Decimal = Field(..., ge=0, description="Общая стоимость товаров")

    model_config = ConfigDict(from_attributes=True)


class OrderItem(BaseModel):
    id: int = Field(..., description="ID позиции заказа")
    product_id: int = Field(..., description="ID товара")
    quantity: int = Field(..., ge=1, description="Количество")
    unit_price: Decimal = Field(..., ge=0, description="Цена за единицу на момент покупки")
    total_price: Decimal = Field(..., ge=0, description="Сумма по позиции")
    product: ProductRead | None = Field(None, description="Полная информация о товаре")

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    id: int = Field(..., description="ID заказа")
    user_id: int = Field(..., description="ID пользователя")
    status: str = Field(..., description="Текущий статус заказа")
    total_amount: Decimal = Field(..., ge=0, description="Общая стоимость")
    created_at: datetime = Field(..., description="Когда заказ был создан")
    updated_at: datetime = Field(..., description="Когда последний раз обновлялся")
    items: list[OrderItem] = Field(default_factory=list, description="Список позиций")

    model_config = ConfigDict(from_attributes=True)


class OrderList(BaseModel):
    items: list[Order] = Field(..., description="Заказы на текущей странице")
    total: int = Field(ge=0, description="Общее количество заказов")
    page: int = Field(ge=1, description="Текущая страница")
    page_size: int = Field(ge=1, description="Размер страницы")

    model_config = ConfigDict(from_attributes=True)


class MediaRead(BaseModel):
    """Схема для отправки id изображения."""
    media_id: uuid4 = Field(
        ...,
        description='Уникальный идентификатор изображения.'
    )

    model_config = ConfigDict(from_attributes=True)
