from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from models.base import TransactionType
from models.category import CategoryKind

class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    transaction_type: TransactionType
    category_type: CategoryKind
    month_limit: int = 1000

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    transaction_type: Optional[TransactionType] = None
    category_type: Optional[CategoryKind] = None
    month_limit: Optional[int] = None

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True
