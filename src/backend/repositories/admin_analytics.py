from sqlalchemy import func, select
from models.category import Category, CategoryKind
from models.financial_transaction import FinancialTransaction
from models.savings_goal import SavingsGoal
from models.user import User
from repositories.financial_transaction import FinancialTransactionRepository


class AdminAnalyticsRepository:
    def __init__(self, session):
        self.session = session

    async def counts(self, year, month):
        start, end = FinancialTransactionRepository.month_bounds(year, month)
        # Scalar subqueries keep this to one round trip and return counts only.
        stmt = select(
            select(func.count()).select_from(User).scalar_subquery(),
            select(func.count()).select_from(FinancialTransaction).scalar_subquery(),
            select(func.count()).select_from(FinancialTransaction).where(
                FinancialTransaction.operation_date >= start,
                FinancialTransaction.operation_date < end).scalar_subquery(),
            select(func.count()).select_from(SavingsGoal).scalar_subquery(),
            select(func.count()).select_from(Category).where(Category.category_type == CategoryKind.CUSTOM).scalar_subquery(),
        )
        return (await self.session.execute(stmt)).one()
