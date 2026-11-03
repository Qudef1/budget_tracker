from datetime import date
from typing import Sequence
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models.financial_transaction import FinancialTransaction
from repositories.base import BaseRepository
from models.base import TransactionType
from models.category import Category


class FinancialTransactionRepository(BaseRepository[FinancialTransaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=FinancialTransaction, session=session)

    async def sum_expenses(self, user_id, category_id, currency, year, month):
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        return await self.session.scalar(select(func.coalesce(func.sum(self.model.amount), 0)).where(
            self.model.user_id == user_id, self.model.category_id == category_id,
            self.model.currency == currency, self.model.transaction_type == TransactionType.EXPENSE,
            self.model.operation_date >= start, self.model.operation_date < end,
        ))

    @staticmethod
    def month_bounds(year, month):
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        return start, end

    async def monthly_totals(self, user_id, year, month, currency):
        start, end = self.month_bounds(year, month)
        stmt = select(
            func.coalesce(func.sum(case((self.model.transaction_type == TransactionType.INCOME, self.model.amount), else_=0)), 0),
            func.coalesce(func.sum(case((self.model.transaction_type == TransactionType.EXPENSE, self.model.amount), else_=0)), 0),
        ).where(self.model.user_id == user_id, self.model.currency == currency,
                self.model.operation_date >= start, self.model.operation_date < end)
        result = await self.session.execute(stmt)
        return result.one()

    async def expenses_by_category(self, user_id, year, month, currency):
        start, end = self.month_bounds(year, month)
        total = func.sum(self.model.amount).label("total")
        stmt = (select(Category.id, Category.name, total)
                .select_from(self.model)
                .outerjoin(Category, and_(Category.id == self.model.category_id, Category.user_id == user_id))
                .where(self.model.user_id == user_id, self.model.currency == currency,
                       self.model.transaction_type == TransactionType.EXPENSE,
                       self.model.operation_date >= start, self.model.operation_date < end)
                .group_by(Category.id, Category.name)
                .order_by(total.desc(), Category.id.asc().nulls_last()))
        return (await self.session.execute(stmt)).all()

    async def get_by_id(self, transaction_id: int, user_id: int) -> FinancialTransaction | None:
        stmt = select(self.model).where(
            self.model.id == transaction_id,
            self.model.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_multi(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[FinancialTransaction]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.operation_date.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_month(
        self, user_id: int, year: int, month: int
    ) -> Sequence[FinancialTransaction]:
        if not 1 <= month <= 12:
            raise ValueError("month must be between 1 and 12")
        start = date(year, month, 1)
        next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.operation_date >= start,
                self.model.operation_date < next_month,
            )
            .order_by(self.model.operation_date.desc(), self.model.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
