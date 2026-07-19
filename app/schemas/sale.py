from pydantic import BaseModel, Field
from app.constants.enums import SaleStatus


class SaleCreate(BaseModel):
    user_id: str
    brand: str = Field(..., min_length=2)
    earning: float = Field(..., gt=0)


class SaleStatusUpdate(BaseModel):
    status: SaleStatus


class ReconciliationRequest(BaseModel):
    status: SaleStatus


class SaleResponse(BaseModel):
    id: str
    user_id: str
    brand: str
    earning: float
    status: SaleStatus
    advance_paid: bool
    advance_amount: float