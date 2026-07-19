from bson import ObjectId
from bson.errors import InvalidId


class BaseRepository:

    def __init__(self, collection):
        self.collection = collection

    async def create(self, data: dict) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def find_by_id(self, document_id: str) -> dict | None:
        try:
            object_id = ObjectId(document_id)
        except InvalidId:
            return None

        return await self.collection.find_one(
            {"_id": object_id}
        )

    async def find_one(self, query: dict) -> dict | None:
        return await self.collection.find_one(query)

    async def find_many(
        self,
        query: dict | None = None
    ) -> list[dict]:

        if query is None:
            query = {}

        cursor = self.collection.find(query)

        return await cursor.to_list(length=None)

    async def update(
        self,
        document_id: str,
        data: dict
    ) -> bool:

        try:
            object_id = ObjectId(document_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {"$set": data},
        )

        return result.modified_count > 0

    async def delete(
        self,
        document_id: str
    ) -> bool:

        try:
            object_id = ObjectId(document_id)
        except InvalidId:
            return False

        result = await self.collection.delete_one(
            {"_id": object_id}
        )

        return result.deleted_count > 0