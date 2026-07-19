from fastapi import APIRouter, HTTPException, status

from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["Wallet"])

wallet_service = WalletService()


@router.get("/{user_id}")
async def get_balance(user_id: str):
    try:
        balance = await wallet_service.get_balance(user_id)

        return {
            "withdrawable_balance": balance
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )