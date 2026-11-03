"""One-time PostgreSQL migration from operations.category to category_id."""

import asyncio

from sqlalchemy import inspect, text

from database import engine
from models.base import Base
from models.category import Category
from models.financial_transaction import FinancialTransaction
from models.user import User


async def migrate():
    async with engine.begin() as connection:
        def schema_info(sync_connection):
            inspector = inspect(sync_connection)
            if not inspector.has_table("operations"):
                return None, False
            return ({column["name"] for column in inspector.get_columns("operations")},
                    inspector.has_table("category"))

        columns, category_exists = await connection.run_sync(schema_info)
        if columns is None:
            print("Таблица operations ещё не создана; миграция не требуется.")
            return
        if "category_id" in columns and "category" not in columns:
            print("Миграция уже выполнена.")
            return
        if "category" not in columns or "category_id" in columns or category_exists:
            raise RuntimeError("Неожиданная схема базы: автоматическая миграция отменена без изменений.")

        await connection.execute(text("LOCK TABLE operations IN ACCESS EXCLUSIVE MODE"))
        await connection.run_sync(lambda sync: Category.__table__.create(sync, checkfirst=True))
        await connection.execute(text("""
            INSERT INTO category (name, transaction_type, category_type, user_id, month_limit)
            SELECT DISTINCT category, transaction_type, CAST('CUSTOM' AS categorykind), user_id, 1000
            FROM operations WHERE category IS NOT NULL
        """))
        await connection.execute(text("ALTER TABLE operations ADD COLUMN category_id INTEGER"))
        await connection.execute(text("""
            UPDATE operations AS o SET category_id = c.id
            FROM category AS c
            WHERE c.name = o.category AND c.user_id = o.user_id
              AND c.transaction_type = o.transaction_type
        """))
        missing = await connection.scalar(text(
            "SELECT count(*) FROM operations WHERE category IS NOT NULL AND category_id IS NULL"
        ))
        if missing:
            raise RuntimeError("Не удалось сопоставить все категории; изменения отменены.")
        await connection.execute(text("ALTER TABLE operations DROP COLUMN category"))
        await connection.execute(text("""
            ALTER TABLE operations ADD CONSTRAINT operations_category_id_fkey
            FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
        """))
        await connection.execute(text("CREATE INDEX ix_operations_category_id ON operations (category_id)"))
        print("Категории перенесены; транзакции сохранены.")


async def main():
    try:
        await migrate()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
