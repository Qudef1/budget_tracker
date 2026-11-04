from decimal import Decimal
from pydantic import BaseModel
from models.base import Currency


class MonthlySummary(BaseModel):
    year: int
    month: int
    currency: Currency
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal


class MonthComparison(BaseModel):
    first: MonthlySummary
    second: MonthlySummary
    income_change: Decimal
    expenses_change: Decimal
    balance_change: Decimal
    income_change_percent: Decimal | None
    expenses_change_percent: Decimal | None


class CategoryExpenses(BaseModel):
    category_id: int | None
    category_name: str | None
    amount: Decimal
    percentage: Decimal


class ExpensesByCategory(BaseModel):
    year: int
    month: int
    currency: Currency
    total_expenses: Decimal
    categories: list[CategoryExpenses]


class AdminStatistics(BaseModel):
    year: int
    month: int
    total_users: int
    blocked_users: int
    total_transactions: int
    monthly_transactions: int
    total_savings_goals: int
    custom_categories: int
