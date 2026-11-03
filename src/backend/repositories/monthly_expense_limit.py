from sqlalchemy import select
from models.monthly_expense_limit import MonthlyExpenseLimit
from repositories.base import BaseRepository


class MonthlyExpenseLimitRepository(BaseRepository[MonthlyExpenseLimit]):
    def __init__(self, session):
        super().__init__(MonthlyExpenseLimit, session)

    async def get_by_id(self, item_id, user_id, *, for_update=False):
        stmt = select(self.model).where(self.model.id == item_id, self.model.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def get_multi(self, user_id, skip=0, limit=100):
        result = await self.session.scalars(select(self.model).where(self.model.user_id == user_id).order_by(self.model.id).offset(skip).limit(limit))
        return result.all()
