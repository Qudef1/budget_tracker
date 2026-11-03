# Saldo FastAPI local demo

This is **local-only** CRUD to test from Swagger UI. It is not secure for deployment:
`get_demo_user_id()` always returns user ID 1 and the `User` table is deliberately minimal.
A real app requires registration, authentication, access checks and a migration system such as Alembic.

## Run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
docker compose ps
cd src/backend
python migrate_categories.py
uvicorn main:app --reload
```

For an existing database, run the migration before starting the new application. It transfers
old category names into per-user categories, separated by transaction type, and preserves
transactions. It is safe to run again after it has completed.

Open http://127.0.0.1:8000/docs and create a category using POST `/categories/`, then use its
`id` in a transaction. The category is optional, and deleting one sets `category_id` to `null`
on its transactions. Try POST `/transactions/`, GET `/transactions/`,
GET `/transactions/month?year=2026&month=11`, PATCH and DELETE.

Sample POST JSON:

```json
{
  "transaction_type": "expense",
  "amount": "42.50",
  "currency": "BYN",
  "category_id": 1,
  "operation_date": "2026-11-03",
  "comment": "Lunch"
}
```

Database via psql:

```powershell
docker compose exec db psql -U saldo -d saldo_db
```

Notes:
- `models/base.py` provides the **only** ORM Base.
- One transaction for each writing endpoint, using `async with session.begin()`;
  repositories only perform `flush()`.
- A user-selectable date is required; none is generated automatically.
- Category must belong to the user and have the same transaction type as the transaction.
- `/monthly-expense-limits/` manages one active limit per user, expense category and currency.
  All stored limits are active; delete a limit to remove it. Deleting a category also deletes
  its limits and their periods while leaving transactions without a category.
- `/execution-limit-periods/` stores a month and year for a limit. Its `expense_amount`,
  `month_limit` and `period_status` are computed when read from matching expense transactions
  and the current limit. A change to the limit also affects the displayed status for past
  periods. Above 80% is `warning`, above 100% is `exceeded`; otherwise it is `not_reached`.
- `/savings-goals/` manages savings targets. `amount` is the target and `status` is the
  nonnegative amount already saved; the saved amount is maintained manually.
- `category.month_limit` is a legacy field and is not used by the new limit calculations.
- DB runs on host 127.0.0.1:55432, inside the container on 5432.
- Changing ORM model definitions won't alter existing tables created by `create_all()`;
  for development use Alembic, or reset only if you can discard all local data.
