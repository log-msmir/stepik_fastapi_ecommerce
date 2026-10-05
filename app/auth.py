from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SECRET_KEY, ALGORITHM
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.models.reviews import Review


ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='users/token')

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Преобразует пароль в безопасный хеш.
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли введённый пароль сохранённому хешу.
    """
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    """
    Создаёт access-токен.
    """
    to_encode = data.copy()
    expire = (
        datetime.now(timezone.utc) + 
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        'exp': expire,
        'token_type': 'access',
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """
    Создаёт refresh-токен с длительным сроком действия и token_type='refresh'.
    """
    to_encode = data.copy()
    expire = (
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        'exp': expire,
        'token_type': 'refresh',
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Проверяет JWT и возвращает пользователя из базы.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')   # New
        if email is None or token_type != 'access':   # New
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = (
        await db.scalars(
            select(UserModel)
            .where(UserModel.email == email, UserModel.is_active == True)
        )
    ).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_seller(
        current_user: UserModel = Depends(get_current_user)
):
    """
    Проверяет, что пользователь имеет роль 'seller'.
    """
    if current_user.role != 'seller':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only sellers can perform this action'
    )
    return current_user


async def get_current_admin(
        current_user: UserModel = Depends(get_current_user)
):
    """
    Проверяет, что пользователь имеет роль 'admin'.
    """
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admin can perform this action'
        )
    return current_user


async def get_current_buyer(
        current_user: UserModel = Depends(get_current_user)
):
    """
    Проверяет, что пользователь имеет роль 'buyer'.
    """
    if current_user.role != 'buyer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admin can perform this action'
    )
    return current_user


async def get_review_or_404(
        review_id: int,
        db: AsyncSession = Depends(get_async_db)
) -> Review:
    """Зависимость для проверки существования отзыва."""
    review = (
        await db.scalars(
            select(Review)
            .where(Review.id == review_id, Review.is_active == True)
        )
    ).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Review not found.'
        )
    return review


async def is_review_author_or_admin(
        review: Review = Depends(get_review_or_404),
        current_user: UserModel = Depends(get_current_user)
) -> Review:
    """Зависимость для проверки прав на работу с отзывом."""
    if review.user_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only author or admin user can perform this action'
        )
    return review
