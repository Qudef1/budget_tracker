from decimal import Decimal, ROUND_HALF_UP

from repositories.admin_analytics import AdminAnalyticsRepository
from repositories.financial_transaction import FinancialTransactionRepository
from schemas.analytics import (AdminStatistics, CategoryExpenses, ExpensesByCategory,
                               MonthComparison, MonthlySummary)


def percentage(numerator, denominator):
    if denominator == 0:
        return None
    return (numerator * Decimal(100) / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class AnalyticsService:
    def __init__(self, session):
        self.transactions = FinancialTransactionRepository(session)

    async def get_monthly_summary(self, user_id, year, month, currency):
        income, expenses = await self.transactions.monthly_totals(user_id, year, month, currency)
        return MonthlySummary(year=year, month=month, currency=currency,
                              total_income=income, total_expenses=expenses, balance=income - expenses)

    async def compare_months(self, user_id, first_year, first_month, second_year, second_month, currency):
        first = await self.get_monthly_summary(user_id, first_year, first_month, currency)
        second = await self.get_monthly_summary(user_id, second_year, second_month, currency)
        income_change = second.total_income - first.total_income
        expenses_change = second.total_expenses - first.total_expenses
        return MonthComparison(first=first, second=second, income_change=income_change,
            expenses_change=expenses_change, balance_change=second.balance - first.balance,
            income_change_percent=percentage(income_change, first.total_income),
            expenses_change_percent=percentage(expenses_change, first.total_expenses))

    async def get_expenses_by_category(self, user_id, year, month, currency):
        rows = await self.transactions.expenses_by_category(user_id, year, month, currency)
        total = sum((row.total for row in rows), Decimal("0"))
        categories = [CategoryExpenses(category_id=row.id, category_name=row.name, amount=row.total,
                         percentage=percentage(row.total, total) or Decimal("0")) for row in rows]
        return ExpensesByCategory(year=year, month=month, currency=currency,
                                  total_expenses=total, categories=categories)


class AdminAnalyticsService:
    """Internal aggregate-only service. A future admin-authorized router may call it."""

    def __init__(self, session):
        self.repo = AdminAnalyticsRepository(session)

    async def get_statistics(self, year, month):
        users, blocked, transactions, monthly, goals, categories = await self.repo.counts(year, month)
        return AdminStatistics(year=year, month=month, total_users=users, blocked_users=blocked,
            total_transactions=transactions, monthly_transactions=monthly,
            total_savings_goals=goals, custom_categories=categories)
