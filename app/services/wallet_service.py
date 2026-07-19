from datetime import datetime

from app.repositories.user_repository import UserRepository


class WalletService:

    def __init__(self):
        self.user_repository = UserRepository()

    async def _get_user(self, user_id: str):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        return user

    async def get_balance(self, user_id: str) -> float:

        user = await self._get_user(user_id)

        return user["withdrawable_balance"]

    async def credit_balance(
        self,
        user_id: str,
        amount: float,
    ) -> float:

        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        user = await self._get_user(user_id)

        new_balance = user["withdrawable_balance"] + amount

        updated = await self.user_repository.update_user(
            user_id,
            {
                "withdrawable_balance": new_balance,
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update wallet balance.")

        return new_balance

    async def debit_balance(
        self,
        user_id: str,
        amount: float,
    ) -> float:

        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        user = await self._get_user(user_id)

        if user["withdrawable_balance"] < amount:
            raise ValueError("Insufficient wallet balance.")

        new_balance = user["withdrawable_balance"] - amount

        updated = await self.user_repository.update_user(
            user_id,
            {
                "withdrawable_balance": new_balance,
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update wallet balance.")

        return new_balance

    async def has_sufficient_balance(
        self,
        user_id: str,
        amount: float,
    ) -> bool:

        balance = await self.get_balance(user_id)

        return balance >= amount