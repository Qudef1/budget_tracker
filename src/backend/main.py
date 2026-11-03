from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import select

from database import AsyncSessionLocal, engine
from models.base import Base
from models.financial_transaction import FinancialTransaction
from models.user import User
from models.category import Category
from models.monthly_expense_limit import MonthlyExpenseLimit
from models.execution_limit_period import ExecutionLimitPeriod
from models.savings_goal import SavingsGoal
from routers.financial_transactions_router import router as transactions_router
from routers.category_router import router as category_router
from routers.budget_router import router as budget_router
from services.budget import BudgetError
from routers.savings_goal_router import router as savings_goal_router
from routers.analytics_router import router as analytics_router


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
app.include_router(category_router)
app.include_router(budget_router)
app.include_router(savings_goal_router)
app.include_router(analytics_router)


@app.exception_handler(BudgetError)
async def budget_error_handler(request, exc: BudgetError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
async def health():
    return {"status": "ok"}
