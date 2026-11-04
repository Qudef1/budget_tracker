from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from repositories.user import UserRepository
from schemas.analytics import AdminStatistics
from schemas.user import UserResponse
from security import require_admin
from services.analytics import AdminAnalyticsService

router = APIRouter(prefix="/admin", tags=["Administration"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserResponse])
async def users(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), session: AsyncSession = Depends(get_async_session)):
    return await UserRepository(session).list_users(skip, limit)


async def set_blocked(user_id, blocked, admin, session):
    if blocked and user_id == admin.id:
        raise HTTPException(403, "Нельзя заблокировать собственную учётную запись")
    async with session.begin():
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id, for_update=True)
        if user is None:
            raise HTTPException(404, "Пользователь не найден")
        await repo.update(user, {"is_blocked": blocked})
    return user


@router.patch("/users/{user_id}/block", response_model=UserResponse)
async def block(user_id: int, admin=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    return await set_blocked(user_id, True, admin, session)


@router.patch("/users/{user_id}/unblock", response_model=UserResponse)
async def unblock(user_id: int, admin=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    return await set_blocked(user_id, False, admin, session)


@router.get("/statistics", response_model=AdminStatistics)
async def statistics(year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), session: AsyncSession = Depends(get_async_session)):
    return await AdminAnalyticsService(session).get_statistics(year, month)
