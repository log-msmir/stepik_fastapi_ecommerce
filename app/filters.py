from datetime import datetime, time

from sqlalchemy import func

from app.schemas import (
    ProductsFilterParams, ProductsOrderingParams, ProductSearchParams
)
from app.models.products import Product


SORT_FIELDS = {
    "created_at": Product.created_at,
}


def get_product_filters(filtering_params: ProductsFilterParams) -> list:
    """Подготовка фильтра для продуктов."""
    filters = [Product.is_active == True]
    if filtering_params.category_id is not None:
        filters.append(
            Product.category_id == filtering_params.category_id
        )
    if filtering_params.min_price is not None:
        filters.append(
             Product.price >= filtering_params.min_price
        )
    if filtering_params.max_price is not None:
        filters.append(
            Product.price <= filtering_params.max_price
        )
    if filtering_params.in_stock is not None:
        filters.append(
            Product.stock > 0 if filtering_params.in_stock else Product.stock == 0
        )
    if filtering_params.seller_id is not None:
        filters.append(
            Product.seller_id == filtering_params.seller_id
        )
    if filtering_params.created_after is not None:
        filters.append(
            Product.created_at >
            datetime.combine(filtering_params.created_after, time.min)
        )
    if filtering_params.created_before is not None:
        filters.append(
            Product.created_at <
            datetime.combine(filtering_params.created_before, time.max)
        )

    return filters


def get_product_ordering(ordering_params: ProductsOrderingParams) -> list:
    if not ordering_params.sort:
        return None

    ordering = [Product.id]
    for param in ordering_params.sort:
        desc_order = param.startswith('-')
        name = param.lstrip('-')
        column = SORT_FIELDS.get(name)
        if column is None:
            continue
        ordering.append(column.desc() if desc_order else column.asc())

    return ordering or None


def get_products_search(search_params: ProductSearchParams) -> list | None:
    """Функция для выполнения простого поиска %LIKE% по товарам."""
    filters = []
    if search_params is not None:
        search_query = search_params.strip()
        if search_query:
            filters.append(
                func.lower(Product.name).like(f'%{search_query.lower()}%')
            )
    return filters if filters else None
