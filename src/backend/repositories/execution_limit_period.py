from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from models.base import TransactionType
from models.execution_limit_period import ExecutionLimitPeriod
from models.financial_transaction import FinancialTransaction
from models.monthly_expense_limit import MonthlyExpenseLimit
from repositories.base import BaseRepository
from schemas.execution_limit_period import PeriodStatus


class ExecutionLimitPeriodRepository(BaseRepository[ExecutionLimitPeriod]):
    def __init__(self, session):
        super().__init__(ExecutionLimitPeriod, session)

    async def get_by_id(self, item_id, user_id):
        return await self.session.scalar(select(self.model).join(MonthlyExpenseLimit).where(
            self.model.id == item_id, MonthlyExpenseLimit.user_id == user_id))

    async def get_multi(self, user_id, skip=0, limit=100):
        result = await self.session.scalars(select(self.model).join(MonthlyExpenseLimit).where(
            MonthlyExpenseLimit.user_id == user_id).order_by(self.model.id).offset(skip).limit(limit))
        return result.all()

    async def to_response(self, period, user_id):
        limit = await self.session.scalar(select(MonthlyExpenseLimit).where(
            MonthlyExpenseLimit.id == period.monthly_expense_limit_id, MonthlyExpenseLimit.user_id == user_id))
        if limit is None:
            return None
        start = date(period.year, period.month, 1)
        end = date(period.year + 1, 1, 1) if period.month == 12 else date(period.year, period.month + 1, 1)
        expense = await self.session.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
            FinancialTransaction.user_id == user_id,
            FinancialTransaction.category_id == limit.category_id,
            FinancialTransaction.currency == limit.currency,
            FinancialTransaction.transaction_type == TransactionType.EXPENSE,
            FinancialTransaction.operation_date >= start,
            FinancialTransaction.operation_date < end,
        ))
        status = (PeriodStatus.EXCEEDED if expense > limit.amount else
                  PeriodStatus.WARNING if expense > limit.amount * Decimal("0.8") else PeriodStatus.NOT_REACHED)
        return dict(id=period.id, monthly_expense_limit_id=limit.id, year=period.year, month=period.month,
                    expense_amount=expense, month_limit=limit.amount, period_status=status)
