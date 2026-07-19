from pydantic import BaseModel
from app.constants.enums import PayoutStatus, PayoutType


class PayoutResponse(BaseModel):
    id: str
    sale_id: str
    user_id: str
    amount: float
    payout_type: PayoutType
    status: PayoutStatus