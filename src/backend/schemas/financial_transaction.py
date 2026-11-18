from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from models.base import Currency, TransactionType

class OperationData(BaseModel):
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=10, decimal_places=2, gt=0)
    currency: Currency = Currency.BYN
    category_id: Optional[int] = Field(None, gt=0)
    operation_date: date
    comment: Optional[str] = Field(None, max_length=500)

class TransactionCreate(OperationData):
    pass

class TransactionUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2, gt=0)
    currency: Optional[Currency] = None
    category_id: Optional[int] = Field(None, gt=0)
    operation_date: Optional[date] = None
    comment: Optional[str] = Field(None, max_length=500)

class TransactionResponse(OperationData):
    id: int

    class Config:
        from_attributes = True
