from sqlalchemy import select
from models.monthly_expense_limit import Limit
from repositories.base import BaseRepository


class MonthlyExpenseLimitRepository(BaseRepository[Limit]):
    def __init__(self, session):
        super().__init__(Limit, session)

    async def get_by_id(self, item_id, user_id, *, for_update=False, include_inactive=False):
        stmt = select(self.model).where(self.model.id == item_id, self.model.user_id == user_id)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def get_multi(self, user_id, skip=0, limit=100):
        result = await self.session.scalars(select(self.model).where(self.model.user_id == user_id, self.model.is_active.is_(True)).order_by(self.model.id).offset(skip).limit(limit))
        return result.all()

    async def get_active(self, user_id, category_id, currency):
        return await self.session.scalar(select(self.model).where(self.model.user_id == user_id,
            self.model.category_id == category_id, self.model.currency == currency, self.model.is_active.is_(True)))
