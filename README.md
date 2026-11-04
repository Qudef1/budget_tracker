# Saldo

FastAPI backend for personal budgeting. Users authenticate with a JWT and can access only
their own financial records; administrators can manage accounts and see aggregate statistics.

## Run the complete app with Docker Compose

From the project root, create `.env` only if you do not already have one, and generate a
private JWT signing key for that new file:

```powershell
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    python -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('JWT_SECRET_KEY=', 'JWT_SECRET_KEY='+secrets.token_urlsafe(48)), encoding='utf-8')"
}
docker compose up -d --build
docker compose ps
```

If `.env` already exists, preserve its `JWT_SECRET_KEY`; it must contain at least 32 bytes.
Do not regenerate the key on each restart: doing so invalidates existing access tokens.
Compose uses the database address `db:5432` inside Docker regardless of the local
`DATABASE_URL` in `.env`. The existing named PostgreSQL volume is preserved.

- App: http://127.0.0.1:5173
- Backend Swagger: http://127.0.0.1:8000/docs
- Logs: `docker compose logs -f backend frontend`
- Stop containers without deleting the database: `docker compose down`
- Create an administrator interactively: `docker compose exec backend python src/backend/create_admin.py`
- Set a password for an existing user interactively: `docker compose exec backend python src/backend/reset_user_password.py`

The backend container runs the existing Alembic, category and budget migration scripts
before starting Uvicorn. These scripts may change the schema and existing records when
upgrading an old database; the previous budget migration cannot reconstruct old limit
amounts that were never stored. Back up data before upgrading an older installation.
For a fresh database, the application creates the remaining tables on startup.
The frontend is built once into a static Nginx image, which forwards `/api/` to the backend.
Run `docker compose up -d --build` again after source changes. These local settings are not
a production deployment configuration.

If a host port is already occupied, set `BACKEND_PORT`, `FRONTEND_PORT` and/or `DB_PORT` before
starting Compose, for example `$env:BACKEND_PORT = '8001'` and
`$env:FRONTEND_PORT = '5174'`. Use those ports in the URLs above. The ports inside
the Docker network do not change.

## Run backend locally (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('JWT_SECRET_KEY=', 'JWT_SECRET_KEY='+secrets.token_urlsafe(48)), encoding='utf-8')"
docker compose up -d db
docker compose ps
.\.venv\Scripts\python.exe -m alembic upgrade head
cd src/backend
python migrate_categories.py
python migrate_budget_history.py
uvicorn main:app --reload
```

For an existing database, run the migration before starting the new application. It transfers
old category names into per-user categories, separated by transaction type, and preserves
transactions. It is safe to run again after it has completed.

On an existing installation, run the Alembic migration before starting the updated app.
Existing users remain active with the `USER` role. The old `demo` user has no usable password;
to retain access to its existing data, run `python src/backend/reset_user_password.py` from the
project root and enter `demo` and a new password interactively. The original data remain in place.

Create an administrator locally with `python src/backend/create_admin.py`; its password is
entered interactively. There is no public administrator registration endpoint. Treat `.env`
and its signing key as secrets, use a unique random key per installation, and keep the key
stable across restarts. `JWT_ACCESS_TOKEN_MINUTES` sets token lifetime.

Open http://127.0.0.1:8000/docs, register via `POST /auth/register`, then click **Authorize**
and supply the username and password. Swagger obtains a bearer token via `POST /auth/login`.
Next create a category using POST `/categories/`, then use its
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
- `/auth/me` returns the active authenticated user. `/admin/users`, its block/unblock routes,
  and `/admin/statistics` require an active administrator. Admin financial routes still use
  the administrator's own user ID and cannot access another user's financial data.
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
