from sqlalchemy import select
from models.savings_goal import SavingsGoal
from repositories.base import BaseRepository


class SavingsGoalRepository(BaseRepository[SavingsGoal]):
    def __init__(self, session):
        super().__init__(SavingsGoal, session)

    async def get_by_id(self, item_id, user_id):
        return await self.session.scalar(select(self.model).where(self.model.id == item_id, self.model.user_id == user_id))

    async def get_multi(self, user_id, skip=0, limit=100):
        result = await self.session.scalars(select(self.model).where(self.model.user_id == user_id).order_by(self.model.id).offset(skip).limit(limit))
        return result.all()
