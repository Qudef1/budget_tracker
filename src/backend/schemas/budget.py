from decimal import Decimal
from pydantic import BaseModel
from schemas.execution_limit_period import PeriodStatus


class LimitResult(BaseModel):
    limit_id: int
    year: int
    month: int
    month_limit: Decimal
    expense_amount: Decimal
    usage_percent: Decimal
    period_status: PeriodStatus
    warning: bool
    exceeded: bool
