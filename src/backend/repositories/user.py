from sqlalchemy import select
from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session):
        super().__init__(User, session)

    async def get_by_id(self, user_id, *, for_update=False):
        stmt = select(User).where(User.id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def get_by_username(self, username):
        return await self.session.scalar(select(User).where(User.username == username))

    async def list_users(self, skip, limit):
        return (await self.session.scalars(select(User).order_by(User.id).offset(skip).limit(limit))).all()
