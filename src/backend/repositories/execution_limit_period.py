from sqlalchemy import select
from models.execution_limit_period import LimitPeriod
from repositories.base import BaseRepository


class ExecutionLimitPeriodRepository(BaseRepository[LimitPeriod]):
    def __init__(self, session):
        super().__init__(LimitPeriod, session)

    async def get_for_month(self, limit_id, year, month):
        return await self.session.scalar(select(self.model).where(
            self.model.monthly_expense_limit_id == limit_id,
            self.model.year == year, self.model.month == month))

    async def get_history(self, limit_id):
        rows = await self.session.scalars(select(self.model).where(
            self.model.monthly_expense_limit_id == limit_id).order_by(self.model.year, self.model.month))
        return list(rows.all())
