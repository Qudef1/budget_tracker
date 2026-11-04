"""PostgreSQL integration tests. Changes are rolled back after each test."""
from datetime import date
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4
import json

from database import AsyncSessionLocal, engine, get_async_session
from main import app
from models.base import Currency, TransactionType
from models.category import Category, CategoryKind
from models.financial_transaction import FinancialTransaction
from models.user import User
from models.savings_goal import SavingsGoal
from services.analytics import AdminAnalyticsService, AnalyticsService
from security import get_current_user_id


class AnalyticsIntegrationTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = AsyncSessionLocal()
        self.transaction = await self.session.begin()
        self.users = [User(id=1_000_000_000 + uuid4().int % 900_000_000,
                           username=f"analytics-{uuid4()}", password_hash="!") for _ in range(2)]
        self.session.add_all(self.users)
        await self.session.flush()
        self.categories = [Category(name=name, transaction_type=TransactionType.EXPENSE,
                                    category_type=CategoryKind.CUSTOM, user_id=self.users[0].id)
                           for name in ("Food", "Transport")]
        self.session.add_all(self.categories)
        await self.session.flush()
        self.service = AnalyticsService(self.session)

    async def asyncTearDown(self):
        await self.transaction.rollback()
        await self.session.close()
        await engine.dispose()

    def add_operation(self, user, amount, kind, currency, when, category=None):
        self.session.add(FinancialTransaction(user_id=user.id, amount=Decimal(amount),
            transaction_type=kind, currency=currency, operation_date=when,
            category_id=category.id if category else None))

    async def test_summary_currency_user_and_december(self):
        user, other = self.users
        income, expense = TransactionType.INCOME, TransactionType.EXPENSE
        self.add_operation(user, '100', income, Currency.BYN, date(2026, 12, 1))
        self.add_operation(user, '45.50', expense, Currency.BYN, date(2026, 12, 31), self.categories[0])
        self.add_operation(user, '70', expense, Currency.USD, date(2026, 12, 1))
        self.add_operation(user, '500', income, Currency.BYN, date(2027, 1, 1))
        self.add_operation(other, '999', income, Currency.BYN, date(2026, 12, 10))
        await self.session.flush()
        summary = await self.service.get_monthly_summary(user.id, 2026, 12, Currency.BYN)
        self.assertEqual((summary.total_income, summary.total_expenses, summary.balance),
                         (Decimal('100'), Decimal('45.50'), Decimal('54.50')))
        usd = await self.service.get_monthly_summary(user.id, 2026, 12, Currency.USD)
        self.assertEqual((usd.total_income, usd.total_expenses, usd.balance), (0, 70, -70))
        january = await self.service.get_monthly_summary(user.id, 2027, 1, Currency.BYN)
        self.assertEqual(january.total_income, 500)
        empty = await self.service.get_monthly_summary(user.id, 2025, 2, Currency.BYN)
        self.assertEqual((empty.total_income, empty.total_expenses, empty.balance), (0, 0, 0))

    async def test_compare_and_zero_denominator(self):
        user = self.users[0]
        for amount, kind, when in [('100', TransactionType.INCOME, date(2024, 3, 1)),
                                   ('40', TransactionType.EXPENSE, date(2024, 3, 2)),
                                   ('150', TransactionType.INCOME, date(2026, 11, 1)),
                                   ('20', TransactionType.EXPENSE, date(2026, 11, 2))]:
            self.add_operation(user, amount, kind, Currency.BYN, when)
        await self.session.flush()
        result = await self.service.compare_months(user.id, 2024, 3, 2026, 11, Currency.BYN)
        self.assertEqual((result.income_change, result.expenses_change, result.balance_change), (50, -20, 70))
        self.assertEqual((result.income_change_percent, result.expenses_change_percent), (50, -50))
        zero = await self.service.compare_months(user.id, 2024, 4, 2026, 11, Currency.BYN)
        self.assertIsNone(zero.income_change_percent)
        self.assertIsNone(zero.expenses_change_percent)

    async def test_categories_including_uncategorized(self):
        user, other = self.users
        when = date(2026, 11, 1)
        for amount, category in [('60', self.categories[0]), ('30', self.categories[1]), ('10', None)]:
            self.add_operation(user, amount, TransactionType.EXPENSE, Currency.BYN, when, category)
        self.add_operation(other, '500', TransactionType.EXPENSE, Currency.BYN, when)
        self.add_operation(user, '500', TransactionType.EXPENSE, Currency.USD, when)
        self.add_operation(user, '500', TransactionType.INCOME, Currency.BYN, when)
        await self.session.flush()
        result = await self.service.get_expenses_by_category(user.id, 2026, 11, Currency.BYN)
        self.assertEqual(result.total_expenses, 100)
        self.assertEqual([c.amount for c in result.categories], [60, 30, 10])
        self.assertEqual([c.percentage for c in result.categories], [60, 30, 10])
        self.assertIsNone(result.categories[-1].category_id)
        empty = await self.service.get_expenses_by_category(user.id, 2025, 1, Currency.BYN)
        self.assertEqual((empty.total_expenses, empty.categories), (0, []))

    async def test_admin_service_is_aggregate_only_and_no_http_endpoint(self):
        admin = AdminAnalyticsService(self.session)
        baseline = await admin.get_statistics(2026, 11)
        self.add_operation(self.users[0], '17', TransactionType.EXPENSE, Currency.BYN, date(2026, 11, 3))
        self.add_operation(self.users[1], '9', TransactionType.EXPENSE, Currency.USD, date(2026, 10, 3))
        self.session.add(SavingsGoal(name='test', amount=100, currency=Currency.BYN, status=0, user_id=self.users[0].id))
        self.session.add(Category(name='new', user_id=self.users[0].id, transaction_type=TransactionType.EXPENSE,
                                  category_type=CategoryKind.CUSTOM))
        await self.session.flush()
        stats = await admin.get_statistics(2026, 11)
        self.assertEqual(stats.total_users, baseline.total_users)
        self.assertEqual(stats.total_transactions - baseline.total_transactions, 2)
        self.assertEqual(stats.monthly_transactions - baseline.monthly_transactions, 1)
        self.assertEqual(stats.total_savings_goals - baseline.total_savings_goals, 1)
        self.assertEqual(stats.custom_categories - baseline.custom_categories, 1)
        self.assertGreaterEqual(stats.blocked_users, 0)
        self.assertEqual(set(stats.model_dump()), {'year', 'month', 'total_users', 'blocked_users',
            'total_transactions', 'monthly_transactions', 'total_savings_goals', 'custom_categories'})
        messages = []
        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        async def send(message):
            messages.append(message)
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'GET',
                 'scheme': 'http', 'path': '/admin/statistics', 'raw_path': b'/admin/statistics',
                 'query_string': b'year=2026&month=11', 'headers': [], 'client': ('127.0.0.1', 1),
                 'server': ('test', 80), 'root_path': ''}
        await app(scope, receive, send)
        self.assertEqual(next(m['status'] for m in messages if m['type'] == 'http.response.start'), 401)

    async def test_http_routes_and_validation(self):
        async def session_override():
            yield self.session
        app.dependency_overrides[get_async_session] = session_override
        app.dependency_overrides[get_current_user_id] = lambda: self.users[0].id

        async def get(path, query):
            messages = []
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            async def send(message):
                messages.append(message)
            await app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'GET',
                       'scheme': 'http', 'path': path, 'raw_path': path.encode(), 'query_string': query.encode(),
                       'headers': [], 'client': ('127.0.0.1', 1), 'server': ('test', 80), 'root_path': ''}, receive, send)
            status = next(m['status'] for m in messages if m['type'] == 'http.response.start')
            body = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
            return status, json.loads(body)
        try:
            self.add_operation(self.users[0], '25', TransactionType.INCOME, Currency.BYN, date(2026, 11, 5))
            await self.session.flush()
            status, result = await get('/analytics/monthly', 'year=2026&month=11&currency=BYN')
            self.assertEqual(status, 200)
            self.assertEqual(Decimal(result['balance']), 25)
            status, result = await get('/analytics/monthly', f'year=2026&month=11&currency=BYN&user_id={self.users[1].id}')
            self.assertEqual(status, 200)
            self.assertEqual(Decimal(result['balance']), 25)
            self.assertEqual((await get('/analytics/categories', 'year=2026&month=11&currency=BYN'))[0], 200)
            self.assertEqual((await get('/analytics/compare', 'first_year=2026&first_month=10&second_year=2026&second_month=11&currency=BYN'))[0], 200)
            self.assertEqual((await get('/analytics/monthly', 'year=2026&month=13&currency=BYN'))[0], 422)
            self.assertEqual((await get('/analytics/monthly', 'year=2026&month=11&currency=EUR'))[0], 422)
            self.assertEqual((await get('/analytics/monthly', 'year=9999&month=11&currency=BYN'))[0], 422)
        finally:
            app.dependency_overrides.clear()
