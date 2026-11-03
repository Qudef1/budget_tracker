from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class PeriodStatus(str, Enum):
    EXCEEDED = "exceeded"
    WARNING = "warning"
    NOT_REACHED = "not_reached"


class ExecutionLimitPeriodCreate(BaseModel):
    monthly_expense_limit_id: int = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1, le=9998)


class ExecutionLimitPeriodResponse(ExecutionLimitPeriodCreate):
    id: int
    expense_amount: Decimal
    month_limit: Decimal
    period_status: PeriodStatus
