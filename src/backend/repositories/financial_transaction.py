from datetime import date
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.financial_transaction import FinancialTransaction
from repositories.base import BaseRepository


class FinancialTransactionRepository(BaseRepository[FinancialTransaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=FinancialTransaction, session=session)

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
