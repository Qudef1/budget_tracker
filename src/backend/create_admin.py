"""Create an administrator locally; credentials are read interactively."""
import asyncio
from getpass import getpass
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from database import AsyncSessionLocal, engine
from models.user import UserRole
from repositories.user import UserRepository
from schemas.user import UserRegister
from security import password_hasher
from fastapi.concurrency import run_in_threadpool


async def create(payload):
    try:
        async with AsyncSessionLocal.begin() as session:
            password_hash = await run_in_threadpool(password_hasher.hash, payload.password)
            await UserRepository(session).create({"username": payload.username, "password_hash": password_hash,
                                                   "role": UserRole.ADMIN, "is_blocked": False})
        print("Administrator created.")
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise SystemExit("Username already exists; no changes made.") from exc
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    username = input("Username: ")
    password = getpass("Password: ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    try:
        payload = UserRegister(username=username, password=password)
    except ValidationError:
        raise SystemExit("Username must contain 3–100 letters, digits, '.', '_' or '-'; password must contain 8–128 characters.")
    asyncio.run(create(payload))
