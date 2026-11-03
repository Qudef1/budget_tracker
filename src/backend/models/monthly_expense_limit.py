from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, Currency


class MonthlyExpenseLimit(Base):
    __tablename__ = "monthly_expense_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "currency", name="uq_monthly_limit_user_category_currency"),
        CheckConstraint("amount > 0", name="ck_monthly_limit_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
