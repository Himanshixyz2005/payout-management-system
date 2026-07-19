from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

database = client[settings.DATABASE_NAME]
