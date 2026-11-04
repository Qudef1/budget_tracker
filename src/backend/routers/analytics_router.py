from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models.base import Currency
from security import get_current_user_id
from schemas.analytics import ExpensesByCategory, MonthComparison, MonthlySummary
from services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/monthly", response_model=MonthlySummary)
async def monthly(year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12),
                  currency: Currency = Query(), session: AsyncSession = Depends(get_async_session),
                  user_id: int = Depends(get_current_user_id)):
    return await AnalyticsService(session).get_monthly_summary(user_id, year, month, currency)


@router.get("/compare", response_model=MonthComparison)
async def compare(first_year: int = Query(ge=1, le=9998), first_month: int = Query(ge=1, le=12),
                  second_year: int = Query(ge=1, le=9998), second_month: int = Query(ge=1, le=12),
                  currency: Currency = Query(), session: AsyncSession = Depends(get_async_session),
                  user_id: int = Depends(get_current_user_id)):
    return await AnalyticsService(session).compare_months(user_id, first_year, first_month, second_year, second_month, currency)


@router.get("/categories", response_model=ExpensesByCategory)
async def categories(year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12),
                     currency: Currency = Query(), session: AsyncSession = Depends(get_async_session),
                     user_id: int = Depends(get_current_user_id)):
    return await AnalyticsService(session).get_expenses_by_category(user_id, year, month, currency)
