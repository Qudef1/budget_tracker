from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models.base import TransactionType
from repositories.category import CategoryRepository
from repositories.monthly_expense_limit import MonthlyExpenseLimitRepository
from routers.financial_transactions_router import get_demo_user_id
from schemas.monthly_expense_limit import MonthlyExpenseLimitCreate, MonthlyExpenseLimitResponse, MonthlyExpenseLimitUpdate

router = APIRouter(prefix="/monthly-expense-limits", tags=["Monthly expense limits"])


@router.post("/", response_model=MonthlyExpenseLimitResponse, status_code=status.HTTP_201_CREATED)
async def create_limit(payload: MonthlyExpenseLimitCreate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    try:
        async with session.begin():
            category = await CategoryRepository(session).get_by_id(payload.category_id, user_id, for_update=True)
            if category is None:
                raise HTTPException(404, "Категория не найдена")
            if category.transaction_type != TransactionType.EXPENSE:
                raise HTTPException(422, "Лимит можно установить только для категории расходов")
            obj = await MonthlyExpenseLimitRepository(session).create({**payload.model_dump(), "user_id": user_id})
        return obj
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Лимит для этой категории и валюты уже существует") from exc
        raise


@router.get("/", response_model=list[MonthlyExpenseLimitResponse])
async def list_limits(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    return await MonthlyExpenseLimitRepository(session).get_multi(user_id, skip, limit)


@router.get("/{item_id}", response_model=MonthlyExpenseLimitResponse)
async def get_limit(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    obj = await MonthlyExpenseLimitRepository(session).get_by_id(item_id, user_id)
    if obj is None:
        raise HTTPException(404, "Лимит не найден")
    return obj


@router.patch("/{item_id}", response_model=MonthlyExpenseLimitResponse)
async def update_limit(item_id: int, payload: MonthlyExpenseLimitUpdate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    data = payload.model_dump(exclude_unset=True)
    if any(value is None for value in data.values()):
        raise HTTPException(422, "Обязательные поля нельзя устанавливать в null")
    repo = MonthlyExpenseLimitRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(item_id, user_id)
        if obj is None:
            raise HTTPException(404, "Лимит не найден")
        await repo.update(obj, data)
    return obj


@router.delete("/{item_id}", status_code=204)
async def delete_limit(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    repo = MonthlyExpenseLimitRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(item_id, user_id)
        if obj is None:
            raise HTTPException(404, "Лимит не найден")
        await repo.delete(obj)
