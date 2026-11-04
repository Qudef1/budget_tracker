from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from repositories.savings_goal import SavingsGoalRepository
from security import get_current_user_id
from schemas.savings_goal import SavingsGoalCreate, SavingsGoalResponse, SavingsGoalUpdate

router = APIRouter(prefix="/savings-goals", tags=["Savings goals"])


@router.post("/", response_model=SavingsGoalResponse, status_code=201)
async def create_goal(payload: SavingsGoalCreate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_current_user_id)):
    async with session.begin():
        obj = await SavingsGoalRepository(session).create({**payload.model_dump(), "user_id": user_id})
    return obj


@router.get("/", response_model=list[SavingsGoalResponse])
async def list_goals(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_current_user_id)):
    return await SavingsGoalRepository(session).get_multi(user_id, skip, limit)


@router.get("/{item_id}", response_model=SavingsGoalResponse)
async def get_goal(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_current_user_id)):
    obj = await SavingsGoalRepository(session).get_by_id(item_id, user_id)
    if obj is None:
        raise HTTPException(404, "Цель не найдена")
    return obj


@router.patch("/{item_id}", response_model=SavingsGoalResponse)
async def update_goal(item_id: int, payload: SavingsGoalUpdate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_current_user_id)):
    data = payload.model_dump(exclude_unset=True)
    if any(value is None for value in data.values()):
        raise HTTPException(422, "Обязательные поля нельзя устанавливать в null")
    repo = SavingsGoalRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(item_id, user_id)
        if obj is None:
            raise HTTPException(404, "Цель не найдена")
        await repo.update(obj, data)
    return obj


@router.delete("/{item_id}", status_code=204)
async def delete_goal(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_current_user_id)):
    repo = SavingsGoalRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(item_id, user_id)
        if obj is None:
            raise HTTPException(404, "Цель не найдена")
        await repo.delete(obj)
