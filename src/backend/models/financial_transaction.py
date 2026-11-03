from sqlalchemy import String, Integer, Date, Enum, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from datetime import date
from typing import Optional
from models.base import Base, TransactionType, Currency

class FinancialTransaction(Base):
    __tablename__ = 'operations'

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10,scale=2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    category: Mapped[int] = mapped_column(
        ForeignKey("category.id"),
        nullable=False,
        index=True
    )
    operation_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    
