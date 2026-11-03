"""Migrate the first budget schema to retained monthly execution snapshots (PostgreSQL)."""
import asyncio

from sqlalchemy import inspect, text
from database import engine
from services.budget import current_month


async def migrate():
    async with engine.begin() as connection:
        def inspect_schema(sync):
            inspector = inspect(sync)
            if not inspector.has_table("monthly_expense_limits"):
                return None
            return {c["name"] for c in inspector.get_columns("monthly_expense_limits")}

        columns = await connection.run_sync(inspect_schema)
        if columns is None:
            print("No budget tables yet; they will be created at startup.")
            return
        if "is_active" in columns:
            print("Budget history migration already applied.")
            return
        await connection.execute(text("LOCK TABLE category, monthly_expense_limits, execution_limit_periods, operations IN ACCESS EXCLUSIVE MODE"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits ADD COLUMN start_month DATE"))
        await connection.execute(text("""
            UPDATE monthly_expense_limits AS l SET start_month = LEAST(CAST(:current AS date),
                COALESCE((SELECT MIN(make_date(p.year, p.month, 1)) FROM execution_limit_periods p
                          WHERE p.monthly_expense_limit_id = l.id), CAST(:current AS date)))
        """), {"current": current_month()})
        await connection.execute(text("ALTER TABLE monthly_expense_limits ALTER COLUMN start_month SET NOT NULL"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits DROP CONSTRAINT uq_monthly_limit_user_category_currency"))
        await connection.execute(text("CREATE UNIQUE INDEX uq_active_monthly_limit ON monthly_expense_limits (user_id, category_id, currency) WHERE is_active"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits DROP CONSTRAINT monthly_expense_limits_category_id_fkey"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits ALTER COLUMN category_id DROP NOT NULL"))
        await connection.execute(text("ALTER TABLE monthly_expense_limits ADD CONSTRAINT monthly_expense_limits_category_id_fkey FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL"))
        await connection.execute(text("ALTER TABLE execution_limit_periods ADD COLUMN month_limit NUMERIC(10,2)"))
        await connection.execute(text("ALTER TABLE execution_limit_periods ADD COLUMN expense_amount NUMERIC(14,2)"))
        await connection.execute(text("ALTER TABLE execution_limit_periods ADD COLUMN is_final BOOLEAN NOT NULL DEFAULT TRUE"))
        await connection.execute(text("""
            UPDATE execution_limit_periods p SET month_limit = l.amount,
                expense_amount = COALESCE((SELECT SUM(o.amount) FROM operations o
                    WHERE o.user_id = l.user_id AND o.category_id = l.category_id
                      AND o.currency = l.currency AND o.transaction_type = 'EXPENSE'
                      AND o.operation_date >= make_date(p.year, p.month, 1)
                      AND o.operation_date < make_date(p.year, p.month, 1) + INTERVAL '1 month'), 0),
                is_final = make_date(p.year, p.month, 1) < CAST(:current AS date)
            FROM monthly_expense_limits l WHERE l.id = p.monthly_expense_limit_id
        """), {"current": current_month()})
        await connection.execute(text("ALTER TABLE execution_limit_periods ALTER COLUMN month_limit SET NOT NULL"))
        await connection.execute(text("ALTER TABLE execution_limit_periods ALTER COLUMN expense_amount SET NOT NULL"))
        print("Budget history migration completed.")


async def main():
    try:
        await migrate()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
