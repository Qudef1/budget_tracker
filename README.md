# Saldo FastAPI local demo

This is **local-only** CRUD to test from Swagger UI. It is not secure for deployment:
`get_demo_user_id()` always returns user ID 1 and the `User` table is deliberately minimal.
A real app requires registration, authentication, access checks, category table and Alembic migrations.

## Run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
docker compose ps
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs and try POST `/transactions/`, GET `/transactions/`,
GET `/transactions/month?year=2026&month=11`, PATCH and DELETE.

Sample POST JSON:

```json
{
  "transaction_type": "expense",
  "amount": "42.50",
  "currency": "BYN",
  "category": "food",
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
- Category is a string placeholder until you implement Category model and category_id FK.
- DB runs on host 127.0.0.1:55432, inside the container on 5432.
- Changing ORM model definitions won't alter existing tables created by `create_all()`;
  for development use Alembic, or reset only if you can discard all local data.
