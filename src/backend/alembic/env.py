import asyncio
from alembic import context
from database import engine
from models.base import Base
from models.user import User
from models.category import Category
from models.financial_transaction import FinancialTransaction
from models.monthly_expense_limit import MonthlyExpenseLimit
from models.execution_limit_period import ExecutionLimitPeriod
from models.savings_goal import SavingsGoal

target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async():
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Online PostgreSQL connection is required")
elif context.config.attributes.get("connection") is not None:
    run_migrations(context.config.attributes["connection"])
else:
    asyncio.run(run_async())
