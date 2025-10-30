from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    client = get_client()
    db = client[settings.mongo_db]
    try:
        yield db
    finally:
        pass
