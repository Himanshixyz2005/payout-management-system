from fastapi import APIRouter, HTTPException, status

from app.schemas.withdrawal import WithdrawalCreate, WithdrawalUpdate
from app.services.withdrawal_service import WithdrawalService

router = APIRouter(
    prefix="/withdrawals",
    tags=["Withdrawals"]
)

withdrawal_service = WithdrawalService()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def withdraw(request: WithdrawalCreate):
    try:
        return await withdrawal_service.withdraw(
            request.user_id,
            request.amount
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{withdrawal_id}/status")
async def update_withdrawal_status(
    withdrawal_id: str,
    request: WithdrawalUpdate,
):
    """Question 2 - mark a payout as FAILED / CANCELLED / REJECTED (or
    SUCCESS). Failure states credit the amount back to the wallet."""
    try:
        return await withdrawal_service.update_withdrawal_status(
            withdrawal_id,
            request.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{user_id}")
async def get_user_withdrawals(user_id: str):
    try:
        return await withdrawal_service.get_user_withdrawals(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
