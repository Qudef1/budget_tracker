from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from routers.financial_transactions_router import get_demo_user_id
from schemas.budget import LimitExecutionResponse
from schemas.monthly_expense_limit import MonthlyExpenseLimitCreate, MonthlyExpenseLimitResponse, MonthlyExpenseLimitUpdate
from services.budget import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("/limits", response_model=MonthlyExpenseLimitResponse, status_code=201)
async def create_limit(payload: MonthlyExpenseLimitCreate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    try:
        async with session.begin():
            return await BudgetService(session).create_limit(user_id, payload)
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Лимит для этой категории и валюты уже существует") from exc
        raise


@router.get("/limits", response_model=list[MonthlyExpenseLimitResponse])
async def get_limits(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    return await BudgetService(session).get_limits(user_id, skip, limit)


@router.patch("/limits/{limit_id}", response_model=MonthlyExpenseLimitResponse)
async def update_limit(limit_id: int, payload: MonthlyExpenseLimitUpdate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    if payload.amount is None:
        raise HTTPException(422, "Укажите сумму лимита")
    async with session.begin():
        return await BudgetService(session).update_limit(user_id, limit_id, payload.amount)


@router.delete("/limits/{limit_id}", status_code=204)
async def delete_limit(limit_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    async with session.begin():
        await BudgetService(session).delete_limit(user_id, limit_id)


@router.get("/limits/{limit_id}/execution", response_model=LimitExecutionResponse)
async def get_limit_execution(limit_id: int, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    return await BudgetService(session).get_limit_execution(user_id, limit_id, year, month)


@router.get("/limits/{limit_id}/history", response_model=list[LimitExecutionResponse])
async def get_limit_history(limit_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    return await BudgetService(session).get_limit_history(user_id, limit_id)
