from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class LimitPeriod(Base):
    __tablename__ = "execution_limit_periods"
    __table_args__ = (
        UniqueConstraint("monthly_expense_limit_id", "year", "month", name="uq_limit_period"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_limit_period_month"),
        CheckConstraint("year BETWEEN 1 AND 9998", name="ck_limit_period_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_expense_limit_id: Mapped[int] = mapped_column(ForeignKey("monthly_expense_limits.id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[int] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    month_limit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expense_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)
