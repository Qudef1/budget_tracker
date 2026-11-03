from datetime import date
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.category import Category
from repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=Category, session=session)

    async def get_by_user_id(self, user_id: int) -> Category | None:
        stmt = select(self.model).where(
            self.model.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_multi(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Category]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.operation_date.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
