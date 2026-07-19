from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserResponse(BaseModel):
    id: str
    username: str
    withdrawable_balance: float
    last_withdrawal_at: Optional[datetime] = None