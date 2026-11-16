"""Create savings goals for new databases; preserve existing installations.

Revision ID: 20261116_savings_goals
Revises: 20261116_budget_history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261116_savings_goals"
down_revision = "20261116_budget_history"
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table("savings_goals"):
        return
    currency = postgresql.ENUM("BYN", "USD", name="currency", create_type=False)
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("status", sa.Numeric(10, 2), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_savings_goal_amount_positive"),
        sa.CheckConstraint("status >= 0", name="ck_savings_goal_status_nonnegative"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])


def downgrade():
    raise RuntimeError("Downgrading savings goals would discard existing savings data")
