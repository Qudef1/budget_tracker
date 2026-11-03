from sqlalchemy.orm import DeclarativeBase
from enum import Enum as PyEnum

class Base(DeclarativeBase):
    pass

class TransactionType(PyEnum):
    INCOME = "income"
    EXPENSE = "expense"

class Currency(PyEnum):
    BYN = "BYN"
    USD = "USD"