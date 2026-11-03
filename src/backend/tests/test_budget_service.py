"""Integration tests; run against a disposable PostgreSQL database with the schema installed."""
from datetime import date
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal, engine
from models.base import Currency, TransactionType
from models.category import Category, CategoryKind
from models.financial_transaction import FinancialTransaction
from models.user import User
from schemas.monthly_expense_limit import MonthlyExpenseLimitCreate
from services.budget import BudgetError, BudgetService


class BudgetServiceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = AsyncSessionLocal()
        self.transaction = await self.session.begin()
        self.user = User(id=1_000_000_000 + uuid4().int % 1_000_000_000,
                         username=f"test-{uuid4()}", password_hash="!")
        self.session.add(self.user)
        await self.session.flush()
        self.category = Category(name="Test", user_id=self.user.id, transaction_type=TransactionType.EXPENSE,
                                 category_type=CategoryKind.CUSTOM, month_limit=1000)
        self.session.add(self.category)
        await self.session.flush()
        self.service = BudgetService(self.session)

    async def asyncTearDown(self):
        await self.transaction.rollback()
        await self.session.close()
        await engine.dispose()

    async def test_history_and_ownership(self):
        user_id = self.user.id
        with patch("services.budget.current_month", return_value=date(2026, 10, 1)):
            limit = await self.service.create_limit(user_id, MonthlyExpenseLimitCreate(
                category_id=self.category.id, amount=100, currency=Currency.BYN))
            tx = FinancialTransaction(user_id=user_id, category_id=self.category.id,
                transaction_type=TransactionType.EXPENSE, amount=Decimal("81"), currency=Currency.BYN,
                operation_date=date(2026, 10, 20))
            self.session.add(tx)
            await self.session.flush()
            result = await self.service.get_limit_execution(user_id, limit.id, 2026, 10)
            self.assertEqual((result["period_status"], result["usage_percent"]), ("warning", 81))
            with self.assertRaises(BudgetError):
                await self.service.get_limit_execution(user_id + 1000000, limit.id, 2026, 10)

        with patch("services.budget.current_month", return_value=date(2026, 11, 1)):
            await self.service.update_limit(user_id, limit.id, Decimal("200"))
            tx.amount = Decimal("20")
            await self.session.flush()
            old = await self.service.get_limit_execution(user_id, limit.id, 2026, 10)
            self.assertEqual((old["month_limit"], old["expense_amount"], old["period_status"]), (100, 81, "warning"))
            await self.service.delete_limit(user_id, limit.id)
            self.assertEqual(len(await self.service.get_limit_history(user_id, limit.id)), 2)
            self.assertEqual(await self.service.get_limits(user_id), [])
            replacement = await self.service.create_limit(user_id, MonthlyExpenseLimitCreate(
                category_id=self.category.id, amount=50, currency=Currency.BYN))
            self.assertNotEqual(replacement.id, limit.id)

    async def test_thresholds_and_expense_filters(self):
        with patch("services.budget.current_month", return_value=date(2026, 11, 1)):
            limit = await self.service.create_limit(self.user.id, MonthlyExpenseLimitCreate(
                category_id=self.category.id, amount=100, currency=Currency.BYN))
            tx = FinancialTransaction(user_id=self.user.id, category_id=self.category.id,
                transaction_type=TransactionType.EXPENSE, amount=80, currency=Currency.BYN,
                operation_date=date(2026, 11, 1))
            self.session.add_all([tx, FinancialTransaction(user_id=self.user.id, category_id=self.category.id,
                transaction_type=TransactionType.EXPENSE, amount=1000, currency=Currency.USD,
                operation_date=date(2026, 11, 1)), FinancialTransaction(user_id=self.user.id,
                category_id=self.category.id, transaction_type=TransactionType.EXPENSE, amount=1000,
                currency=Currency.BYN, operation_date=date(2026, 10, 31))])
            await self.session.flush()
            for amount, expected in [("80", "not_reached"), ("80.01", "warning"),
                                     ("100", "warning"), ("100.01", "exceeded")]:
                tx.amount = Decimal(amount)
                await self.session.flush()
                result = await self.service.get_limit_execution(self.user.id, limit.id, 2026, 11)
                self.assertEqual(result["period_status"], expected)
                self.assertEqual(result["expense_amount"], Decimal(amount))
