from fastapi import APIRouter

from app.services.advance_payout_service import AdvancePayoutService

router = APIRouter(
    prefix="/payouts",
    tags=["Advance Payouts"]
)

advance_service = AdvancePayoutService()


@router.post("/advance")
async def process_advance_payouts():
    return await advance_service.process_advance_payouts()