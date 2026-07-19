from datetime import datetime

from app.constants.enums import PayoutStatus, PayoutType, SaleStatus
from app.repositories.sale_repository import SaleRepository
from app.repositories.payout_repository import PayoutRepository
from app.services.wallet_service import WalletService


class ReconciliationService:

    def __init__(self):
        self.sale_repository = SaleRepository()
        self.payout_repository = PayoutRepository()
        self.wallet_service = WalletService()

    async def reconcile_sale(
        self,
        sale_id: str,
        final_status: SaleStatus,
    ):

        sale = await self.sale_repository.find_by_id(sale_id)

        if not sale:
            raise ValueError("Sale not found.")

        if sale["status"] != SaleStatus.PENDING:
            raise ValueError("Sale has already been reconciled.")

        if final_status == SaleStatus.APPROVED:

            remaining_amount = round(
                sale["earning"] - sale["advance_amount"],
                2,
            )

            if remaining_amount > 0:

                await self.wallet_service.credit_balance(
                    sale["user_id"],
                    remaining_amount,
                )

                payout = {
                    "user_id": sale["user_id"],
                    "sale_id": sale_id,
                    "amount": remaining_amount,
                    "type": PayoutType.FINAL.value,
                    "status": PayoutStatus.SUCCESS.value,
                    "created_at": datetime.utcnow(),
                }

                await self.payout_repository.create(payout)

        elif final_status == SaleStatus.REJECTED:

            recovery_amount = sale["advance_amount"]

            if recovery_amount > 0:

                try:
                    await self.wallet_service.debit_balance(
                        sale["user_id"],
                        recovery_amount,
                    )

                    recovery = {
                        "user_id": sale["user_id"],
                        "sale_id": sale_id,
                        "amount": recovery_amount,
                        "type": PayoutType.ADJUSTMENT.value,
                        "status": PayoutStatus.SUCCESS.value,
                        "created_at": datetime.utcnow(),
                    }

                except ValueError:

                    recovery = {
                        "user_id": sale["user_id"],
                        "sale_id": sale_id,
                        "amount": recovery_amount,
                        "type": PayoutType.ADJUSTMENT.value,
                        "status": PayoutStatus.FAILED.value,
                        "created_at": datetime.utcnow(),
                    }

                await self.payout_repository.create(recovery)

        updated = await self.sale_repository.update_sale(
            sale_id,
            {
                "status": final_status,
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update sale.")

        return {
            "sale_id": sale_id,
            "status": final_status,
        }