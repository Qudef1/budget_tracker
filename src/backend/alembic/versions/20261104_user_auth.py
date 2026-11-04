"""Add authentication attributes while preserving existing users.

Revision ID: 20261104_user_auth
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261104_user_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    role = postgresql.ENUM("USER", "ADMIN", name="userrole", create_type=False)
    role.create(connection, checkfirst=True)
    if not inspector.has_table("users"):
        op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(100), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", role, nullable=False, server_default="USER"),
            sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()))
    else:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in columns:
            op.add_column("users", sa.Column("role", role, nullable=False, server_default="USER"))
        if "is_blocked" not in columns:
            op.add_column("users", sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()))
        uniques = inspector.get_unique_constraints("users")
        indexes = inspector.get_indexes("users")
        if not any(c.get("column_names") == ["username"] for c in uniques) and not any(
                i.get("unique") and i.get("column_names") == ["username"] for i in indexes):
            op.create_unique_constraint("uq_users_username", "users", ["username"])
    # The old startup inserted user id=1 explicitly, leaving the sequence behind.
    op.execute(sa.text("""SELECT setval(pg_get_serial_sequence('users', 'id'),
        GREATEST(COALESCE((SELECT MAX(id) FROM users), 0), 1),
        EXISTS(SELECT 1 FROM users))"""))


def downgrade():
    raise RuntimeError("Downgrading authentication would discard user roles and block state")
