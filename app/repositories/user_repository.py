from app.database.database import database
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):

    def __init__(self):
        super().__init__(database["users"])

    async def get_by_username(self, username: str):
        return await self.find_one(
            {
                "username": username
            }
        )

    async def get_all_users(self):
        return await self.find_many()

    async def update_user(self, user_id: str, data: dict):
        return await self.update(user_id, data)