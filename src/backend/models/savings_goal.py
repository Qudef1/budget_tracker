from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, Currency


class Goal(Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_savings_goal_amount_positive"),
        CheckConstraint("status >= 0", name="ck_savings_goal_status_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    status: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
