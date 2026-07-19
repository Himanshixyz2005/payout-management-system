from datetime import datetime

from app.constants.enums import SaleStatus
from app.repositories.sale_repository import SaleRepository
from app.repositories.user_repository import UserRepository


class SaleService:

    def __init__(self):
        self.sale_repository = SaleRepository()
        self.user_repository = UserRepository()

    async def create_sale(
        self,
        user_id: str,
        brand: str,
        earning: float,
    ):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        sale = {
            "user_id": user_id,
            "brand": brand,
            "earning": earning,
            "status": SaleStatus.PENDING,
            "advance_paid": False,
            "advance_amount": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        sale_id = await self.sale_repository.create(sale)

        # insert_one mutates `sale` by injecting a raw ObjectId `_id`,
        # which is not JSON-serializable; drop it before returning.
        sale.pop("_id", None)

        return {
            "id": sale_id,
            **sale,
        }

    async def get_sale(
        self,
        sale_id: str,
    ):

        sale = await self.sale_repository.find_by_id(sale_id)

        if not sale:
            raise ValueError("Sale not found.")

        sale["id"] = str(sale["_id"])
        sale.pop("_id")

        return sale

    async def get_user_sales(
        self,
        user_id: str,
    ):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        sales = await self.sale_repository.get_sales_by_user(user_id)

        for sale in sales:
            sale["id"] = str(sale["_id"])
            sale.pop("_id")

        return sales

    async def update_sale_status(
        self,
        sale_id: str,
        status: SaleStatus,
    ):

        sale = await self.sale_repository.find_by_id(sale_id)

        if not sale:
            raise ValueError("Sale not found.")

        if sale["status"] != SaleStatus.PENDING:
            raise ValueError("Sale has already been reconciled.")

        updated = await self.sale_repository.update_sale(
            sale_id,
            {
                "status": status,
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update sale.")
        

        

        return True

        