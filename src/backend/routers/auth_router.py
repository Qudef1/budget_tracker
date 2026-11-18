from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from schemas.user import TokenResponse, UserRegister, UserResponse
from security import get_current_active_user
from services.auth import AuthController

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegister, session: AsyncSession = Depends(get_async_session)):
    try:
        async with session.begin():
            return await AuthController(session).register(payload)
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Логин уже занят") from exc
        raise


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_async_session)):
    service = AuthController(session)
    user = await service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль", headers={"WWW-Authenticate": "Bearer"})
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись заблокирована")
    return TokenResponse(access_token=service.issue_token(user))


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_active_user)):
    return user
