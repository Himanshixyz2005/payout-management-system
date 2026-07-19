from app.constants.enums import SaleStatus
from app.database.database import database
from app.repositories.base_repository import BaseRepository


class SaleRepository(BaseRepository):

    def __init__(self):
        super().__init__(database["sales"])

    async def get_pending_sales(self):
        return await self.find_many(
            {
                "status": SaleStatus.PENDING,
                "advance_paid": False,
            }
        )

    async def get_sales_by_user(self, user_id: str):
        return await self.find_many(
            {
                "user_id": user_id
            }
        )

    async def update_sale(self, sale_id: str, data: dict):
        return await self.update(sale_id, data)