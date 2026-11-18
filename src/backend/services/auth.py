from fastapi.concurrency import run_in_threadpool
from pwdlib.exceptions import UnknownHashError

from models.user import UserRole
from repositories.user import UserRepository
from security import create_access_token, password_hasher


class AuthController:
    def __init__(self, session):
        self.users = UserRepository(session)

    async def register(self, payload):
        password_hash = await run_in_threadpool(password_hasher.hash, payload.password)
        return await self.users.create({"username": payload.username, "password_hash": password_hash,
                                        "role": UserRole.USER, "is_blocked": False})

    async def authenticate(self, username, password):
        user = await self.users.get_by_username(username)
        if user is None or len(password) > 128:
            return None
        try:
            valid = await run_in_threadpool(password_hasher.verify, password, user.password_hash)
        except (UnknownHashError, ValueError):
            valid = False
        return user if valid else None

    def issue_token(self, user):
        return create_access_token(user.id)
