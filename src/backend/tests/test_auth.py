"""End-to-end authentication tests against the configured PostgreSQL database."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import jwt
from sqlalchemy import delete, select

from database import AsyncSessionLocal, engine
from main import app
from models.category import Category
from models.execution_limit_period import LimitPeriod
from models.financial_transaction import Operation
from models.monthly_expense_limit import Limit
from models.savings_goal import Goal
from models.user import User, UserRole
from security import password_hasher, settings


def test_authentication_and_authorization():
    asyncio.run(run_scenario())


async def run_scenario():
    suffix = uuid4().hex
    names = [f"auth-{suffix}-a", f"auth-{suffix}-b", f"auth-{suffix}-admin"]
    password = "test-password-123"
    ids = []
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get('/auth/me')).status_code == 401
            for username in names[:2]:
                response = await client.post('/auth/register', json={'username': username, 'password': password})
                assert response.status_code == 201, response.text
                data = response.json()
                assert data['role'] == 'USER' and not data['is_blocked'] and 'password_hash' not in data
                ids.append(data['id'])
            assert (await client.post('/auth/register', json={'username': names[0], 'password': password})).status_code == 409
            assert (await client.post('/auth/register', json={'username': 'bad', 'password': password, 'role': 'ADMIN'})).status_code == 422
            async with AsyncSessionLocal.begin() as session:
                users = (await session.scalars(select(User).where(User.id.in_(ids)))).all()
                assert all(user.password_hash != password and user.password_hash.startswith('$argon2') for user in users)
                admin = User(username=names[2], password_hash=password_hasher.hash(password), role=UserRole.ADMIN)
                session.add(admin)
                await session.flush()
                ids.append(admin.id)
            async def login(username, pwd=password):
                return await client.post('/auth/login', data={'username': username, 'password': pwd})
            assert (await login(names[0], 'wrong')).status_code == 401
            assert (await login('nonexistent-user')).status_code == 401
            headers = []
            for name in names:
                response = await login(name)
                assert response.status_code == 200, response.text
                headers.append({'Authorization': 'Bearer ' + response.json()['access_token']})
            a, b, admin = headers
            assert (await client.get('/auth/me', headers=a)).json()['id'] == ids[0]
            secret, _ = settings()
            now = datetime.now(timezone.utc)
            expired = jwt.encode({'sub': str(ids[0]), 'iat': now - timedelta(hours=2), 'exp': now - timedelta(hours=1)}, secret, algorithm='HS256')
            wrong = jwt.encode({'sub': str(ids[0]), 'iat': now, 'exp': now + timedelta(hours=1)}, 'wrong-key-at-least-thirty-two-bytes', algorithm='HS256')
            missing_claim = jwt.encode({'sub': str(ids[0]), 'exp': now + timedelta(hours=1)}, secret, algorithm='HS256')
            missing_user = jwt.encode({'sub': '2147483647', 'iat': now, 'exp': now + timedelta(hours=1)}, secret, algorithm='HS256')
            for token in [expired, wrong, missing_claim, missing_user, 'bad.token.value']:
                assert (await client.get('/auth/me', headers={'Authorization': 'Bearer ' + token})).status_code == 401
            assert (await client.get('/admin/users', headers=a)).status_code == 403
            assert (await client.get('/admin/statistics?year=2026&month=11', headers=a)).status_code == 403
            users_result = await client.get('/admin/users', headers=admin)
            assert users_result.status_code == 200 and all('password_hash' not in u for u in users_result.json())
            stats = await client.get('/admin/statistics?year=2026&month=11', headers=admin)
            assert stats.status_code == 200 and 'total_users' in stats.json() and 'total_income' not in stats.json()
            assert (await client.patch(f'/admin/users/{ids[2]}/block', headers=admin)).status_code == 403
            category = await client.post('/categories/', headers=a, json={'name': 'Private', 'transaction_type': 'expense', 'category_type': 'custom'})
            assert category.status_code == 201, category.text
            cid = category.json()['id']
            tx = await client.post('/transactions/', headers=a, json={'transaction_type': 'expense', 'amount': '42', 'currency': 'BYN', 'category_id': cid, 'operation_date': '2026-11-01'})
            assert tx.status_code == 201, tx.text
            txid = tx.json()['id']
            assert (await client.get(f'/transactions/{txid}', headers=a)).status_code == 200
            for foreign in [b, admin]:
                assert (await client.get(f'/transactions/{txid}', headers=foreign)).status_code == 404
                assert (await client.patch(f'/transactions/{txid}', headers=foreign, json={'amount': '1'})).status_code == 404
                assert (await client.delete(f'/transactions/{txid}', headers=foreign)).status_code == 404
                assert (await client.get(f'/categories/{cid}', headers=foreign)).status_code == 404
                assert (await client.patch(f'/categories/{cid}', headers=foreign, json={'name': 'stolen'})).status_code == 404
                assert (await client.delete(f'/categories/{cid}', headers=foreign)).status_code == 404
                analytic = await client.get(f'/analytics/monthly?year=2026&month=11&currency=BYN&user_id={ids[0]}', headers=foreign)
                assert analytic.status_code == 200 and Decimal(analytic.json()['total_expenses']) == 0
            goal = await client.post('/savings-goals/', headers=a, json={'name':'Goal', 'amount':'100', 'currency':'BYN'})
            assert goal.status_code == 201, goal.text
            gid = goal.json()['id']
            assert (await client.get(f'/savings-goals/{gid}', headers=b)).status_code == 404
            assert (await client.patch(f'/savings-goals/{gid}', headers=b, json={'status':'10'})).status_code == 404
            assert (await client.delete(f'/savings-goals/{gid}', headers=b)).status_code == 404
            budget = await client.post('/budgets/limits', headers=a, json={'amount': '100', 'currency': 'BYN', 'category_id': cid})
            assert budget.status_code == 201, budget.text
            bid = budget.json()['id']
            assert (await client.patch(f'/budgets/limits/{bid}', headers=b, json={'amount':'1'})).status_code == 404
            assert (await client.get(f'/budgets/limits/{bid}/history', headers=b)).status_code == 404
            assert (await client.get(f'/budgets/limits/{bid}/execution?year=2026&month=11', headers=b)).status_code == 404
            assert (await client.delete(f'/budgets/limits/{bid}', headers=b)).status_code == 404
            assert (await client.post('/transactions/', headers=b, json={'transaction_type': 'expense', 'amount':'1', 'currency':'BYN', 'category_id':cid, 'operation_date':'2026-11-01'})).status_code == 404
            assert (await client.patch(f'/admin/users/{ids[0]}/block', headers=admin)).status_code == 200
            assert (await client.patch(f'/admin/users/{ids[0]}/block', headers=admin)).status_code == 200
            assert (await login(names[0])).status_code == 403
            assert (await client.get('/auth/me', headers=a)).status_code == 403
            assert (await client.get('/transactions/', headers=a)).status_code == 403
            assert (await client.patch(f'/admin/users/{ids[0]}/unblock', headers=admin)).status_code == 200
            assert (await client.patch(f'/admin/users/{ids[0]}/unblock', headers=admin)).status_code == 200
            assert (await client.get('/auth/me', headers=a)).status_code == 200
    finally:
        if ids:
            async with AsyncSessionLocal.begin() as session:
                limit_ids = select(Limit.id).where(Limit.user_id.in_(ids))
                await session.execute(delete(LimitPeriod).where(LimitPeriod.monthly_expense_limit_id.in_(limit_ids)))
                for model in (Operation, Limit, Goal, Category):
                    await session.execute(delete(model).where(model.user_id.in_(ids)))
                await session.execute(delete(User).where(User.id.in_(ids)))
        await engine.dispose()
