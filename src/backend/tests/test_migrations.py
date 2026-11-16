"""Exercise real Alembic upgrades in isolated PostgreSQL schemas, rolled back per test."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import shutil
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from dotenv import load_dotenv
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from models.base import Base
from models.category import Category  # noqa: F401 -- populate ORM metadata
from models.execution_limit_period import ExecutionLimitPeriod  # noqa: F401
from models.financial_transaction import FinancialTransaction  # noqa: F401
from models.monthly_expense_limit import MonthlyExpenseLimit  # noqa: F401
from models.savings_goal import SavingsGoal  # noqa: F401
from models.user import User  # noqa: F401


ROOT = Path(__file__).resolve().parents[3]
AUTH = "20261104_user_auth"
CATEGORIES = "20261116_categories"
HEAD = "20261116_savings_goals"


def alembic_config(connection):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "src/backend/alembic"))
    config.attributes["connection"] = connection
    return config


def run_in_schema(scenario):
    async def run():
        load_dotenv(ROOT / ".env")
        url = os.environ.get("MIGRATION_TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    schema = "migration_test_" + uuid4().hex
                    await connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
                    await connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
                    # AsyncConnection.run_sync lets Alembic use the same connection and
                    # transaction; nothing is applied to the installation's own tables.
                    await connection.run_sync(scenario)
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()
    asyncio.run(run())


def execute(connection, sql, **parameters):
    return connection.execute(sa.text(sql), parameters)


def assert_current_schema(connection):
    assert execute(connection, "SELECT version_num FROM alembic_version").scalar_one() == HEAD
    assert set(sa.inspect(connection).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
    assert compare_metadata(context, Base.metadata) == []


def seed_users(connection):
    execute(connection, "INSERT INTO users (id, username, password_hash) VALUES (1, 'one', '!'), (2, 'two', '!')")


def seed_category(connection):
    execute(connection, """
        INSERT INTO category (id, name, transaction_type, category_type, user_id, month_limit)
        VALUES (1, 'Food', 'EXPENSE', 'CUSTOM', 1, 1000)
    """)


def test_empty_database_and_repeated_upgrade():
    def scenario(connection):
        config = alembic_config(connection)
        command.upgrade(config, "head")
        assert_current_schema(connection)
        seed_users(connection)
        seed_category(connection)
        command.upgrade(config, "head")
        assert_current_schema(connection)
        assert execute(connection, "SELECT count(*) FROM users").scalar_one() == 2
        assert execute(connection, "SELECT name FROM category").scalar_one() == "Food"
    run_in_schema(scenario)


def test_legacy_category_names_preserve_ownership_types_and_operations():
    def scenario(connection):
        config = alembic_config(connection)
        command.upgrade(config, AUTH)
        seed_users(connection)
        execute(connection, "CREATE TYPE transactiontype AS ENUM ('INCOME', 'EXPENSE')")
        execute(connection, "CREATE TYPE currency AS ENUM ('BYN', 'USD')")
        execute(connection, """
            CREATE TABLE operations (
                id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                transaction_type transactiontype NOT NULL, amount NUMERIC(10,2) NOT NULL,
                currency currency NOT NULL, category VARCHAR(100), operation_date DATE NOT NULL,
                comment VARCHAR(500)
            )
        """)
        execute(connection, "CREATE INDEX ix_operations_user_id ON operations (user_id)")
        execute(connection, """
            INSERT INTO operations (user_id, transaction_type, amount, currency, category, operation_date, comment)
            VALUES (1, 'EXPENSE', 10, 'BYN', 'Food', '2026-10-01', 'retained'),
                   (1, 'EXPENSE', 20, 'BYN', 'Food', '2026-10-02', NULL),
                   (1, 'INCOME', 30, 'BYN', 'Food', '2026-10-03', NULL),
                   (2, 'EXPENSE', 40, 'BYN', 'Food', '2026-10-04', NULL),
                   (1, 'EXPENSE', 50, 'USD', NULL, '2026-10-05', NULL)
        """)
        command.upgrade(config, "head")
        assert_current_schema(connection)
        assert execute(connection, "SELECT count(*) FROM category").scalar_one() == 3
        assert execute(connection, "SELECT sum(amount) FROM operations").scalar_one() == 150
        assert execute(connection, "SELECT comment FROM operations WHERE id = 1").scalar_one() == "retained"
        assert execute(connection, "SELECT category_id FROM operations WHERE id = 5").scalar_one() is None
        assert execute(connection, """
            SELECT count(*) FROM operations o JOIN category c ON c.id = o.category_id
            WHERE o.user_id = c.user_id AND o.transaction_type = c.transaction_type
              AND c.name = 'Food' AND c.category_type = 'CUSTOM' AND c.month_limit = 1000
        """).scalar_one() == 4
        execute(connection, "DELETE FROM category")
        assert execute(connection, "SELECT count(*) FROM operations WHERE category_id IS NULL").scalar_one() == 5
    run_in_schema(scenario)


def test_legacy_budget_history_backfills_snapshots_and_archive_support():
    def scenario(connection):
        config = alembic_config(connection)
        command.upgrade(config, CATEGORIES)
        seed_users(connection)
        seed_category(connection)
        execute(connection, """
            CREATE TABLE monthly_expense_limits (
                id SERIAL PRIMARY KEY, amount NUMERIC(10,2) NOT NULL,
                currency currency NOT NULL, category_id INTEGER NOT NULL REFERENCES category(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                CONSTRAINT uq_monthly_limit_user_category_currency UNIQUE (user_id, category_id, currency),
                CONSTRAINT ck_monthly_limit_amount_positive CHECK (amount > 0)
            )
        """)
        execute(connection, "CREATE INDEX ix_monthly_expense_limits_category_id ON monthly_expense_limits (category_id)")
        execute(connection, "CREATE INDEX ix_monthly_expense_limits_user_id ON monthly_expense_limits (user_id)")
        execute(connection, """
            CREATE TABLE execution_limit_periods (
                id SERIAL PRIMARY KEY,
                monthly_expense_limit_id INTEGER NOT NULL REFERENCES monthly_expense_limits(id) ON DELETE CASCADE,
                month INTEGER NOT NULL, year INTEGER NOT NULL,
                CONSTRAINT uq_limit_period UNIQUE (monthly_expense_limit_id, year, month),
                CONSTRAINT ck_limit_period_month CHECK (month BETWEEN 1 AND 12),
                CONSTRAINT ck_limit_period_year CHECK (year BETWEEN 1 AND 9998)
            )
        """)
        execute(connection, "CREATE INDEX ix_execution_limit_periods_monthly_expense_limit_id ON execution_limit_periods (monthly_expense_limit_id)")
        current = datetime.now(timezone(timedelta(hours=3))).date().replace(day=1)
        previous = (current - timedelta(days=1)).replace(day=1)
        execute(connection, "INSERT INTO monthly_expense_limits (amount, currency, category_id, user_id) VALUES (100, 'BYN', 1, 1), (200, 'USD', 1, 1)")
        for month in (previous, current):
            execute(connection, "INSERT INTO execution_limit_periods (monthly_expense_limit_id, year, month) VALUES (1, :year, :month)", year=month.year, month=month.month)
        execute(connection, """
            INSERT INTO operations (user_id, transaction_type, amount, currency, category_id, operation_date)
            VALUES (1, 'EXPENSE', 42.50, 'BYN', 1, :previous),
                   (1, 'EXPENSE', 3.50, 'BYN', 1, :current),
                   (2, 'EXPENSE', 999, 'BYN', 1, :previous),
                   (1, 'INCOME', 999, 'BYN', 1, :previous),
                   (1, 'EXPENSE', 999, 'USD', 1, :previous)
        """, previous=previous, current=current)
        command.upgrade(config, "head")
        assert_current_schema(connection)
        rows = execute(connection, "SELECT month_limit, expense_amount, is_final FROM execution_limit_periods ORDER BY year, month").all()
        assert rows == [(100, Decimal("42.50"), True), (100, Decimal("3.50"), False)]
        assert execute(connection, "SELECT start_month FROM monthly_expense_limits ORDER BY id").scalars().all() == [previous, current]
        execute(connection, "UPDATE monthly_expense_limits SET is_active = FALSE WHERE id = 1")
        execute(connection, "INSERT INTO monthly_expense_limits (amount, currency, category_id, user_id, start_month) VALUES (75, 'BYN', 1, 1, :current)", current=current)
        execute(connection, "DELETE FROM category WHERE id = 1")
        assert execute(connection, "SELECT count(*) FROM monthly_expense_limits WHERE category_id IS NULL").scalar_one() == 3
        assert execute(connection, "SELECT expense_amount FROM execution_limit_periods ORDER BY year, month").scalars().all() == [Decimal("42.50"), Decimal("3.50")]
    run_in_schema(scenario)


@pytest.mark.parametrize("stamped", [False, True])
def test_already_migrated_installation_preserves_data(stamped):
    def scenario(connection):
        Base.metadata.create_all(connection)
        config = alembic_config(connection)
        if stamped:
            command.stamp(config, AUTH)
        seed_users(connection)
        seed_category(connection)
        execute(connection, """
            INSERT INTO monthly_expense_limits (id, amount, currency, category_id, user_id, is_active, start_month)
            VALUES (1, 200, 'BYN', NULL, 1, FALSE, '2025-01-01')
        """)
        execute(connection, """
            INSERT INTO execution_limit_periods (monthly_expense_limit_id, year, month, month_limit, expense_amount, is_final)
            VALUES (1, 2025, 1, 100, 25.55, TRUE)
        """)
        execute(connection, "INSERT INTO savings_goals (name, amount, currency, status, user_id) VALUES ('Laptop', 500, 'USD', 123, 1)")
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        assert_current_schema(connection)
        assert execute(connection, "SELECT amount, category_id, is_active FROM monthly_expense_limits").one() == (200, None, False)
        assert execute(connection, "SELECT month_limit, expense_amount, is_final FROM execution_limit_periods").one() == (100, Decimal("25.55"), True)
        assert execute(connection, "SELECT name, status FROM savings_goals").one() == ("Laptop", 123)
        if not stamped:
            assert execute(connection, "INSERT INTO users (username, password_hash) VALUES ('three', '!') RETURNING id").scalar_one() == 3
    run_in_schema(scenario)


def test_failed_category_conversion_rolls_back_schema_and_revision():
    def scenario(connection):
        config = alembic_config(connection)
        command.upgrade(config, AUTH)
        seed_users(connection)
        execute(connection, "CREATE TYPE transactiontype AS ENUM ('INCOME', 'EXPENSE')")
        execute(connection, "CREATE TYPE currency AS ENUM ('BYN', 'USD')")
        execute(connection, """
            CREATE TABLE operations (
                id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                transaction_type transactiontype NOT NULL, amount NUMERIC(10,2) NOT NULL,
                currency currency NOT NULL, category TEXT, operation_date DATE NOT NULL,
                comment VARCHAR(500)
            )
        """)
        execute(connection, "INSERT INTO operations (user_id, transaction_type, amount, currency, category, operation_date) VALUES (1, 'EXPENSE', 10, 'BYN', :category, '2026-01-01')", category="x" * 101)
        with pytest.raises(sa.exc.DBAPIError):
            with connection.begin_nested():
                command.upgrade(config, "head")
        assert not sa.inspect(connection).has_table("category")
        assert "category" in {c["name"] for c in sa.inspect(connection).get_columns("operations")}
        assert execute(connection, "SELECT category FROM operations").scalar_one() == "x" * 101
        assert execute(connection, "SELECT version_num FROM alembic_version").scalar_one() == AUTH
    run_in_schema(scenario)


def test_partially_migrated_budget_schema_is_rejected():
    def scenario(connection):
        Base.metadata.create_all(connection)
        config = alembic_config(connection)
        command.stamp(config, CATEGORIES)
        execute(connection, "ALTER TABLE monthly_expense_limits DROP COLUMN start_month")
        with pytest.raises(RuntimeError, match="Unexpected budget schema"):
            command.upgrade(config, "head")
        assert execute(connection, "SELECT version_num FROM alembic_version").scalar_one() == CATEGORIES
        assert "start_month" not in {c["name"] for c in sa.inspect(connection).get_columns("monthly_expense_limits")}
    run_in_schema(scenario)


def test_new_revision_template(tmp_path):
    scripts = tmp_path / "alembic"
    shutil.copytree(ROOT / "src/backend/alembic", scripts, ignore=shutil.ignore_patterns("__pycache__"))
    config = Config()
    config.set_main_option("script_location", str(scripts))
    generated = command.revision(config, message="Next schema change")
    assert generated.down_revision == HEAD
    source = Path(generated.path).read_text(encoding="utf-8")
    compile(source, generated.path, "exec")
    assert "def upgrade():" in source and "def downgrade():" in source
