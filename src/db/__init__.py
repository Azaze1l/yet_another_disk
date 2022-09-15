import logging

from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings

logger = logging.getLogger('events')


class Database:
    client: AsyncIOMotorClient

    def __init__(self, client):
        self.client = client


db = Database(client=AsyncIOMotorClient(
        settings.MONGODB_CONNECTION_URL,
        serverSelectionTimeoutMS=10,
    )
)


async def connect_to_mongodb():
    logger.info('Connecting to MongoDB')
    logger.info('Obtained MongoDB connection')
    #
    # all specified on mongo startup procedures here
    #
    logger.info('All DB specific procedures completed')


async def close_mongodb_connection():
    logger.info('Closing MongoDB connections')
    db.client.close()


async def get_db():
    return db.client[settings.MONGO_DB]
