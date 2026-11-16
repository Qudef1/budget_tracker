"""Create categories and operations, or migrate legacy category names.

Revision ID: 20261116_categories
Revises: 20261104_user_auth
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261116_categories"
down_revision = "20261104_user_auth"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    operations_exist = inspector.has_table("operations")
    category_exists = inspector.has_table("category")
    columns = {c["name"] for c in inspector.get_columns("operations")} if operations_exist else set()
    legacy = "category" in columns
    if operations_exist and (
        (legacy and ("category_id" in columns or category_exists))
        or (not legacy and ("category_id" not in columns or not category_exists))
    ):
        raise RuntimeError("Unexpected category schema; migration cancelled without changes")

    transaction_type = postgresql.ENUM("INCOME", "EXPENSE", name="transactiontype", create_type=False)
    category_kind = postgresql.ENUM("SYSTEM", "CUSTOM", name="categorykind", create_type=False)
    currency = postgresql.ENUM("BYN", "USD", name="currency", create_type=False)
    for enum in (transaction_type, category_kind, currency):
        enum.create(connection, checkfirst=True)

    if legacy:
        op.execute("LOCK TABLE operations IN ACCESS EXCLUSIVE MODE")
    if not category_exists:
        op.create_table(
            "category",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("transaction_type", transaction_type, nullable=False),
            sa.Column("category_type", category_kind, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("month_limit", sa.Integer(), nullable=False),
        )
        op.create_index("ix_category_user_id", "category", ["user_id"])

    if not operations_exist:
        op.create_table(
            "operations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("transaction_type", transaction_type, nullable=False),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", currency, nullable=False),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id", ondelete="SET NULL")),
            sa.Column("operation_date", sa.Date(), nullable=False),
            sa.Column("comment", sa.String(500)),
        )
        op.create_index("ix_operations_user_id", "operations", ["user_id"])
        op.create_index("ix_operations_category_id", "operations", ["category_id"])
    elif legacy:
        op.execute("""
            INSERT INTO category (name, transaction_type, category_type, user_id, month_limit)
            SELECT DISTINCT category, transaction_type, CAST('CUSTOM' AS categorykind), user_id, 1000
            FROM operations WHERE category IS NOT NULL
        """)
        op.add_column("operations", sa.Column("category_id", sa.Integer()))
        op.execute("""
            UPDATE operations AS o SET category_id = c.id
            FROM category AS c
            WHERE c.name = o.category AND c.user_id = o.user_id
              AND c.transaction_type = o.transaction_type
        """)
        missing = connection.scalar(sa.text(
            "SELECT count(*) FROM operations WHERE category IS NOT NULL AND category_id IS NULL"
        ))
        if missing:
            raise RuntimeError("Could not match all categories; migration cancelled without changes")
        op.drop_column("operations", "category")
        op.create_foreign_key("operations_category_id_fkey", "operations", "category", ["category_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_operations_category_id", "operations", ["category_id"])


def downgrade():
    raise RuntimeError("Downgrading categories would discard category identities and associations")
