FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src/backend
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./
COPY src/backend ./src/backend

EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python src/backend/migrate_categories.py && python src/backend/migrate_budget_history.py && exec uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir src/backend"]
