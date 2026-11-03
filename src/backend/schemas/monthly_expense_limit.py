from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from models.base import Currency


class MonthlyExpenseLimitCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: Currency
    category_id: int = Field(gt=0)


class MonthlyExpenseLimitUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class MonthlyExpenseLimitResponse(MonthlyExpenseLimitCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
