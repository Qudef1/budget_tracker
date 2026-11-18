from decimal import Decimal

from datetime import date, datetime, timedelta, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey, Index, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, Currency


class Limit(Base):
    __tablename__ = "monthly_expense_limits"
    __table_args__ = (
        Index("uq_active_monthly_limit", "user_id", "category_id", "currency", unique=True, postgresql_where=text("is_active")),
        CheckConstraint("amount > 0", name="ck_monthly_limit_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    start_month: Mapped[date] = mapped_column(Date, nullable=False, default=lambda: datetime.now(timezone(timedelta(hours=3))).date().replace(day=1))
