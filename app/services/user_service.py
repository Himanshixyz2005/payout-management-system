from datetime import datetime

from app.repositories.user_repository import UserRepository


class UserService:

    def __init__(self):
        self.user_repository = UserRepository()

    async def create_user(self, username: str):

        existing_user = await self.user_repository.get_by_username(username)

        if existing_user:
            raise ValueError("Username already exists.")

        user = {
            "username": username,
            "withdrawable_balance": 0.0,
            "last_withdrawal_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        user_id = await self.user_repository.create(user)

        return {
            "id": user_id,
            "username": username,
            "withdrawable_balance": 0.0,
            "last_withdrawal_at": None,
        }

    async def get_user(self, user_id: str):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        user["id"] = str(user["_id"])
        user.pop("_id")

        return user

    async def get_all_users(self):

        users = await self.user_repository.get_all_users()

        for user in users:
            user["id"] = str(user["_id"])
            user.pop("_id")

        return users

    async def update_wallet_balance(
        self,
        user_id: str,
        balance: float,
    ):

        updated = await self.user_repository.update_user(
            user_id,
            {
                "withdrawable_balance": balance,
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update wallet balance.")

        return True

    async def update_last_withdrawal(
        self,
        user_id: str,
    ):

        updated = await self.user_repository.update_user(
            user_id,
            {
                "last_withdrawal_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )

        if not updated:
            raise ValueError("Unable to update withdrawal time.")

        return True