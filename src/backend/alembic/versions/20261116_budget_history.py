"""Create budget tables or retain monthly snapshots from the legacy schema.

Revision ID: 20261116_budget_history
Revises: 20261116_categories
"""
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261116_budget_history"
down_revision = "20261116_categories"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    limits_exist = inspector.has_table("monthly_expense_limits")
    periods_exist = inspector.has_table("execution_limit_periods")
    limit_columns = {c["name"] for c in inspector.get_columns("monthly_expense_limits")} if limits_exist else set()
    period_columns = {c["name"] for c in inspector.get_columns("execution_limit_periods")} if periods_exist else set()
    limit_fields = {"is_active", "start_month"}
    period_fields = {"month_limit", "expense_amount", "is_final"}
    legacy = limits_exist and not (limit_fields & limit_columns)
    if (
        (periods_exist and not limits_exist)
        or (legacy and (not periods_exist or period_fields & period_columns))
        or (not legacy and limits_exist and not limit_fields <= limit_columns)
        or (not legacy and periods_exist and not period_fields <= period_columns)
    ):
        raise RuntimeError("Unexpected budget schema; migration cancelled without changes")

    if not limits_exist:
        currency = postgresql.ENUM("BYN", "USD", name="currency", create_type=False)
        op.create_table(
            "monthly_expense_limits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", currency, nullable=False),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id", ondelete="SET NULL")),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("start_month", sa.Date(), nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_monthly_limit_amount_positive"),
        )
        op.create_index("ix_monthly_expense_limits_category_id", "monthly_expense_limits", ["category_id"])
        op.create_index("ix_monthly_expense_limits_user_id", "monthly_expense_limits", ["user_id"])
        op.create_index("uq_active_monthly_limit", "monthly_expense_limits", ["user_id", "category_id", "currency"], unique=True, postgresql_where=sa.text("is_active"))

    if not periods_exist:
        op.create_table(
            "execution_limit_periods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("monthly_expense_limit_id", sa.Integer(), sa.ForeignKey("monthly_expense_limits.id", ondelete="CASCADE"), nullable=False),
            sa.Column("month", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("month_limit", sa.Numeric(10, 2), nullable=False),
            sa.Column("expense_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("monthly_expense_limit_id", "year", "month", name="uq_limit_period"),
            sa.CheckConstraint("month BETWEEN 1 AND 12", name="ck_limit_period_month"),
            sa.CheckConstraint("year BETWEEN 1 AND 9998", name="ck_limit_period_year"),
        )
        op.create_index("ix_execution_limit_periods_monthly_expense_limit_id", "execution_limit_periods", ["monthly_expense_limit_id"])

    if legacy:
        _migrate_history(connection)


def _migrate_history(connection):
    current = datetime.now(timezone(timedelta(hours=3))).date().replace(day=1)
    op.execute("LOCK TABLE category, monthly_expense_limits, execution_limit_periods, operations IN ACCESS EXCLUSIVE MODE")
    op.add_column("monthly_expense_limits", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("monthly_expense_limits", sa.Column("start_month", sa.Date()))
    connection.execute(sa.text("""
        UPDATE monthly_expense_limits AS l SET start_month = LEAST(CAST(:current AS date),
            COALESCE((SELECT MIN(make_date(p.year, p.month, 1)) FROM execution_limit_periods p
                      WHERE p.monthly_expense_limit_id = l.id), CAST(:current AS date)))
    """), {"current": current})
    op.alter_column("monthly_expense_limits", "start_month", nullable=False)
    op.drop_constraint("uq_monthly_limit_user_category_currency", "monthly_expense_limits", type_="unique")
    op.create_index("uq_active_monthly_limit", "monthly_expense_limits", ["user_id", "category_id", "currency"], unique=True, postgresql_where=sa.text("is_active"))
    op.drop_constraint("monthly_expense_limits_category_id_fkey", "monthly_expense_limits", type_="foreignkey")
    op.alter_column("monthly_expense_limits", "category_id", nullable=True)
    op.create_foreign_key("monthly_expense_limits_category_id_fkey", "monthly_expense_limits", "category", ["category_id"], ["id"], ondelete="SET NULL")
    op.add_column("execution_limit_periods", sa.Column("month_limit", sa.Numeric(10, 2)))
    op.add_column("execution_limit_periods", sa.Column("expense_amount", sa.Numeric(14, 2)))
    op.add_column("execution_limit_periods", sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.true()))
    connection.execute(sa.text("""
        UPDATE execution_limit_periods p SET month_limit = l.amount,
            expense_amount = COALESCE((SELECT SUM(o.amount) FROM operations o
                WHERE o.user_id = l.user_id AND o.category_id = l.category_id
                  AND o.currency = l.currency AND o.transaction_type = 'EXPENSE'
                  AND o.operation_date >= make_date(p.year, p.month, 1)
                  AND o.operation_date < make_date(p.year, p.month, 1) + INTERVAL '1 month'), 0),
            is_final = make_date(p.year, p.month, 1) < CAST(:current AS date)
        FROM monthly_expense_limits l WHERE l.id = p.monthly_expense_limit_id
    """), {"current": current})
    op.alter_column("execution_limit_periods", "month_limit", nullable=False)
    op.alter_column("execution_limit_periods", "expense_amount", nullable=False)


def downgrade():
    raise RuntimeError("Downgrading budget history would discard retained monthly snapshots")
