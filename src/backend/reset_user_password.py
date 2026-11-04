"""Set an existing user's password locally without changing their identity or data."""
import asyncio
from getpass import getpass
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from database import AsyncSessionLocal, engine
from repositories.user import UserRepository
from schemas.user import UserRegister
from security import password_hasher


async def reset(payload):
    try:
        async with AsyncSessionLocal.begin() as session:
            repo = UserRepository(session)
            user = await repo.get_by_username(payload.username)
            if user is None:
                raise SystemExit("User not found.")
            new_hash = await run_in_threadpool(password_hasher.hash, payload.password)
            await repo.update(user, {"password_hash": new_hash})
        print("Password updated.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    username = input("Username: ")
    password = getpass("New password: ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    try:
        payload = UserRegister(username=username, password=password)
    except ValidationError:
        raise SystemExit("Username must contain 3–100 letters, digits, '.', '_' or '-'; password must contain 8–128 characters.")
    asyncio.run(reset(payload))
