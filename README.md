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
python migrate_budget_history.py
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
- `/budgets/limits` creates and lists active limits; PATCH and DELETE use `/budgets/limits/{id}`.
  At most one limit is active for a user, expense category and currency. A limit begins in
  the current month (UTC+3) and repeats automatically. Changes apply to the current month;
  earlier months are saved as snapshots before an update or deletion. Before a snapshot is
  saved, expenses and status reflect the current transactions. Deletion archives the limit;
  deleting a category also archives its limits and removes the category from transactions.
- `/budgets/limits/{id}/execution?year=2026&month=11` returns the monthly amount spent,
  limit, percentage and status; `/budgets/limits/{id}/history` returns monthly history,
  including after deletion. Future months and months before creation are not available.
  Above 80% is `warning`, above 100% is `exceeded`; otherwise it is `not_reached`.
- `/savings-goals/` manages savings targets. `amount` is the target and `status` is the
  nonnegative amount already saved; the saved amount is maintained manually.
- `/analytics/monthly`, `/analytics/compare`, and `/analytics/categories` calculate
  user totals from transactions for one currency. Month comparison is second minus first;
  undefined percentage changes return `null`. Categories with no category ID are grouped
  together with `category_id` and `category_name` set to `null`.
- The application currently uses a fixed demo user and has no authentication or admin role.
  Admin statistics are available only as an internal service, not as an HTTP endpoint;
  blocked user counts are unavailable because the user model has no blocking field.
- `category.month_limit` is a legacy field and is not used by the new limit calculations.
- DB runs on host 127.0.0.1:55432, inside the container on 5432.
- Changing ORM model definitions won't alter existing tables created by `create_all()`;
  for development use Alembic, or reset only if you can discard all local data.
- `migrate_budget_history.py` upgrades the earlier budget tables without deleting existing
  limits or periods. Earlier period values are reconstructed using the limit amount and
  transaction data available at migration time; old limit changes cannot be recovered.

For integration tests, install `pip install -r requirements-dev.txt` and run
`python -m pytest tests` from `src/backend` against PostgreSQL with the schema installed.
Test records are inserted inside transactions that are rolled back.
