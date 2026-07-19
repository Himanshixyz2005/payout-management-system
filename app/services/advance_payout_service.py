from datetime import datetime

from app.constants.enums import PayoutStatus, PayoutType
from app.repositories.sale_repository import SaleRepository
from app.repositories.payout_repository import PayoutRepository
from app.services.wallet_service import WalletService


class AdvancePayoutService:

    ADVANCE_PERCENTAGE = 0.10

    def __init__(self):
        self.sale_repository = SaleRepository()
        self.payout_repository = PayoutRepository()
        self.wallet_service = WalletService()

    async def process_advance_payouts(self):

        pending_sales = await self.sale_repository.get_pending_sales()

        processed_sales = 0
        total_amount_paid = 0.0

        for sale in pending_sales:

            if sale["advance_paid"]:
                continue

            advance_amount = round(
                sale["earning"] * self.ADVANCE_PERCENTAGE,
                2,
            )

            if advance_amount <= 0:
                continue

            await self.wallet_service.credit_balance(
                sale["user_id"],
                advance_amount,
            )

            payout = {
                "user_id": sale["user_id"],
                "sale_id": str(sale["_id"]),
                "amount": advance_amount,
                "type": PayoutType.ADVANCE.value,
                "status": PayoutStatus.SUCCESS.value,
                "created_at": datetime.utcnow(),
            }

            await self.payout_repository.create(payout)

            await self.sale_repository.update_sale(
                str(sale["_id"]),
                {
                    "advance_paid": True,
                    "advance_amount": advance_amount,
                    "updated_at": datetime.utcnow(),
                },
            )

            processed_sales += 1
            total_amount_paid += advance_amount

        return {
            "processed_sales": processed_sales,
            "total_amount_paid": total_amount_paid,
        }