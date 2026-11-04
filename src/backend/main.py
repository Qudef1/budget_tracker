from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import select

from database import engine
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
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from security import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings()
    # Demo only: use Alembic migrations in a real application.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


app = FastAPI(title="Saldo API", lifespan=lifespan)
app.include_router(transactions_router)
app.include_router(category_router)
app.include_router(budget_router)
app.include_router(savings_goal_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.exception_handler(BudgetError)
async def budget_error_handler(request, exc: BudgetError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
async def health():
    return {"status": "ok"}
