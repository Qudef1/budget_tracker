from sqlalchemy import String, Integer, Date, Enum, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TransactionType
from enum import Enum as PyEnum

class CategoryKind(str, PyEnum):
    SYSTEM = "system"
    CUSTOM = "custom"

class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(Integer,primary_key=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

    category_type: Mapped[CategoryKind] = mapped_column(Enum(CategoryKind), nullable=False)

    user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id"),
            nullable=False,
            index=True
    )

    month_limit: Mapped[int] = mapped_column(Integer, default=1000)

