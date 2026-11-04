import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.user import UserRole
from repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
password_hasher = PasswordHash.recommended()


def settings():
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
    try:
        minutes = int(os.environ.get("JWT_ACCESS_TOKEN_MINUTES", "30"))
    except ValueError as exc:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be a positive integer") from exc
    if minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be a positive integer")
    return secret, minutes


def create_access_token(user_id):
    secret, minutes = settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=minutes)}, secret, algorithm="HS256")


async def get_auth_session():
    # Authentication reads have their own session so application write transactions
    # can explicitly begin without colliding with SQLAlchemy autobegin.
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_auth_session)):
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен", headers={"WWW-Authenticate": "Bearer"})
    try:
        secret, _ = settings()
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "exp", "iat"]})
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdigit() or not 0 < int(subject) <= 2147483647:
            raise invalid
        if (type(claims["iat"]) is not int or type(claims["exp"]) is not int
                or claims["exp"] <= claims["iat"]):
            raise invalid
        user = await UserRepository(session).get_by_id(int(subject))
    except (jwt.InvalidTokenError, ValueError, OverflowError):
        raise invalid
    if user is None:
        raise invalid
    return user


async def get_current_active_user(user=Depends(get_current_user)):
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись заблокирована")
    return user


async def get_current_user_id(user=Depends(get_current_active_user)):
    return user.id


async def require_admin(user=Depends(get_current_active_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права администратора")
    return user
