from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from repositories.execution_limit_period import ExecutionLimitPeriodRepository
from repositories.monthly_expense_limit import MonthlyExpenseLimitRepository
from routers.financial_transactions_router import get_demo_user_id
from schemas.execution_limit_period import ExecutionLimitPeriodCreate, ExecutionLimitPeriodResponse

router = APIRouter(prefix="/execution-limit-periods", tags=["Execution limit periods"])


@router.post("/", response_model=ExecutionLimitPeriodResponse, status_code=201)
async def create_period(payload: ExecutionLimitPeriodCreate, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    repo = ExecutionLimitPeriodRepository(session)
    try:
        async with session.begin():
            if await MonthlyExpenseLimitRepository(session).get_by_id(payload.monthly_expense_limit_id, user_id, for_update=True) is None:
                raise HTTPException(404, "Лимит не найден")
            obj = await repo.create(payload.model_dump())
            result = await repo.to_response(obj, user_id)
        return result
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, "Период для этого лимита уже существует") from exc
        raise


@router.get("/", response_model=list[ExecutionLimitPeriodResponse])
async def list_periods(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    repo = ExecutionLimitPeriodRepository(session)
    periods = await repo.get_multi(user_id, skip, limit)
    return [await repo.to_response(obj, user_id) for obj in periods]


@router.get("/{item_id}", response_model=ExecutionLimitPeriodResponse)
async def get_period(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    repo = ExecutionLimitPeriodRepository(session)
    obj = await repo.get_by_id(item_id, user_id)
    if obj is None:
        raise HTTPException(404, "Период не найден")
    return await repo.to_response(obj, user_id)


@router.delete("/{item_id}", status_code=204)
async def delete_period(item_id: int, session: AsyncSession = Depends(get_async_session), user_id: int = Depends(get_demo_user_id)):
    repo = ExecutionLimitPeriodRepository(session)
    async with session.begin():
        obj = await repo.get_by_id(item_id, user_id)
        if obj is None:
            raise HTTPException(404, "Период не найден")
        await repo.delete(obj)
