from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from models.base import Currency


class SavingsGoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: Currency
    status: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class SavingsGoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: Currency | None = None
    status: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class SavingsGoalResponse(SavingsGoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
