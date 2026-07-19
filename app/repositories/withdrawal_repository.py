from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.constants.enums import WithdrawalStatus
from app.database.database import database
from app.repositories.base_repository import BaseRepository


class WithdrawalRepository(BaseRepository):

    def __init__(self):
        super().__init__(database["withdrawals"])

    async def get_last_withdrawal(self, user_id: str) -> dict | None:
        return await self.collection.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )

    async def get_last_active_withdrawal(
        self,
        user_id: str,
        active_statuses: list[str],
    ) -> dict | None:
        """Most recent withdrawal that still holds money out of the wallet.

        Used to recompute the 24h withdrawal lock after a payout is
        reversed, so a failed payout never counts against the limit.
        """
        return await self.collection.find_one(
            {
                "user_id": user_id,
                "status": {"$in": active_statuses},
            },
            sort=[("created_at", -1)],
        )

    async def get_user_withdrawals(self, user_id: str) -> list[dict]:
        return await self.find_many(
            {"user_id": user_id}
        )

    async def update_withdrawal_status(
        self,
        withdrawal_id: str,
        status: WithdrawalStatus
    ) -> bool:
        return await self.update(
            withdrawal_id,
            {
                "status": status,
                "updated_at": datetime.utcnow(),
            }
        )

    async def transition_status_if_current(
        self,
        withdrawal_id: str,
        new_status: str,
        allowed_current: list[str],
    ) -> bool:
        """Atomically flip status only if it is currently one of
        `allowed_current`.

        Returns True for exactly one caller, which makes the balance
        credit-back on failure recovery safe against duplicate calls
        (see Question 2 in the README).
        """
        try:
            object_id = ObjectId(withdrawal_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {
                "_id": object_id,
                "status": {"$in": allowed_current},
            },
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return result.modified_count == 1
