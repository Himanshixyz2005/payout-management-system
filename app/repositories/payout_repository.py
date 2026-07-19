from app.database.database import database
from app.repositories.base_repository import BaseRepository


class PayoutRepository(BaseRepository):

    def __init__(self):
        super().__init__(database["payouts"])

    async def get_user_payouts(self, user_id: str):
        return await self.find_many(
            {
                "user_id": user_id
            }
        )

    async def get_sale_payouts(self, sale_id: str):
        return await self.find_many(
            {
                "sale_id": sale_id
            }
        )

    async def update_payout_status(
        self,
        payout_id: str,
        status: str,
    ):
        return await self.update(
            payout_id,
            {
                "status": status
            },
        )