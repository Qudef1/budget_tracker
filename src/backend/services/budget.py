from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from models.base import TransactionType
from repositories.category import CategoryRepository
from repositories.execution_limit_period import ExecutionLimitPeriodRepository
from repositories.financial_transaction import FinancialTransactionRepository
from repositories.monthly_expense_limit import MonthlyExpenseLimitRepository


class BudgetError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def current_month():
    return datetime.now(timezone(timedelta(hours=3))).date().replace(day=1)


def next_month(value):
    return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)


class BudgetController:
    def __init__(self, session):
        self.limits = MonthlyExpenseLimitRepository(session)
        self.periods = ExecutionLimitPeriodRepository(session)
        self.transactions = FinancialTransactionRepository(session)
        self.categories = CategoryRepository(session)

    async def create_limit(self, user_id, payload):
        category = await self.categories.get_by_id(payload.category_id, user_id, for_update=True)
        if category is None:
            raise BudgetError(404, "Категория не найдена")
        if category.transaction_type != TransactionType.EXPENSE:
            raise BudgetError(422, "Лимит можно установить только для категории расходов")
        if await self.limits.get_active(user_id, payload.category_id, payload.currency):
            raise BudgetError(409, "Лимит для этой категории и валюты уже существует")
        return await self.limits.create({**payload.model_dump(), "user_id": user_id, "start_month": current_month()})

    async def get_limits(self, user_id, skip=0, limit=100):
        return await self.limits.get_multi(user_id, skip, limit)

    async def _get_limit(self, user_id, limit_id, *, include_inactive=False, for_update=False):
        obj = await self.limits.get_by_id(limit_id, user_id, include_inactive=include_inactive, for_update=for_update)
        if obj is None:
            raise BudgetError(404, "Лимит не найден")
        return obj

    async def _execution(self, obj, month, period=None):
        period = period or await self.periods.get_for_month(obj.id, month.year, month.month)
        if period is not None and period.is_final:
            amount, expense = period.month_limit, period.expense_amount
        else:
            if not obj.is_active or obj.category_id is None:
                raise BudgetError(404, "Нет данных за этот месяц")
            amount = obj.amount
            expense = await self.transactions.sum_expenses(obj.user_id, obj.category_id, obj.currency, month.year, month.month)
        ratio = expense / amount
        status = "exceeded" if ratio > 1 else "warning" if ratio > Decimal("0.8") else "not_reached"
        return {"limit_id": obj.id, "year": month.year, "month": month.month, "month_limit": amount,
                "expense_amount": expense, "usage_percent": (ratio * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "period_status": status, "warning": ratio > Decimal("0.8") and ratio <= 1, "exceeded": ratio > 1}

    async def _freeze(self, obj, include_current=False):
        month, last = obj.start_month, current_month()
        while month < last or (include_current and month == last):
            period = await self.periods.get_for_month(obj.id, month.year, month.month)
            if period is None or not period.is_final:
                result = await self._execution(obj, month, period)
                data = {"month_limit": result["month_limit"], "expense_amount": result["expense_amount"], "is_final": True}
                if period is None:
                    await self.periods.create({**data, "monthly_expense_limit_id": obj.id, "year": month.year, "month": month.month})
                else:
                    await self.periods.update(period, data)
            month = next_month(month)

    async def update_limit(self, user_id, limit_id, amount):
        obj = await self._get_limit(user_id, limit_id, for_update=True)
        await self._freeze(obj)
        obj.amount = amount
        await self.limits.session.flush()
        return obj

    async def delete_limit(self, user_id, limit_id):
        obj = await self._get_limit(user_id, limit_id, for_update=True)
        await self._freeze(obj, include_current=True)
        obj.is_active = False
        await self.limits.session.flush()

    async def get_limit_execution(self, user_id, limit_id, year, month):
        obj = await self._get_limit(user_id, limit_id, include_inactive=True)
        when = date(year, month, 1)
        if when < obj.start_month or when > current_month():
            raise BudgetError(404, "Лимит не действовал в этом месяце")
        return await self._execution(obj, when)

    async def get_limit_history(self, user_id, limit_id):
        obj = await self._get_limit(user_id, limit_id, include_inactive=True)
        saved = {(p.year, p.month): p for p in await self.periods.get_history(obj.id)}
        if not obj.is_active:
            return [await self._execution(obj, date(p.year, p.month, 1), p) for p in saved.values() if p.is_final]
        result, month, last = [], obj.start_month, current_month()
        while month <= last:
            result.append(await self._execution(obj, month, saved.get((month.year, month.month))))
            month = next_month(month)
        return result
