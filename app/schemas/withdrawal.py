from pydantic import BaseModel, Field
from app.constants.enums import WithdrawalStatus


class WithdrawalCreate(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0)


class WithdrawalUpdate(BaseModel):
    status: WithdrawalStatus


class WithdrawalResponse(BaseModel):
    id: str
    amount: float
    status: WithdrawalStatus