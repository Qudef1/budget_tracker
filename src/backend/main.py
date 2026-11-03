from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from database import AsyncSessionLocal, engine
from models.base import Base
from models.financial_transaction import FinancialTransaction
from models.user import User
from routers.financial_transactions_router import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demo only: use Alembic migrations in a real application.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Demo identity for Swagger CRUD. No real authentication yet.
    async with AsyncSessionLocal.begin() as session:
        existing = await session.get(User, 1)
        if existing is None:
            # This is not a valid password hash; demo login is not supported.
            session.add(User(id=1, username="demo", password_hash="!"))

    yield
    await engine.dispose()


app = FastAPI(title="Saldo API (local demo)", lifespan=lifespan)
app.include_router(transactions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
