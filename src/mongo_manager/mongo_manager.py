from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from loguru import logger


class MongoManager:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db: AsyncIOMotorDatabase = None

    async def connect(self) -> AsyncIOMotorDatabase:
        """Connect to MongoDB and return the database object."""
        try:
            mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.getenv("MONGO_DB_NAME", "kingdom_shop")

            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[db_name]

            # Test the connection
            await self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")

            return self.db

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database object. Connect if not already connected."""
        if self.db is None:
            await self.connect()
        return self.db


# Global instance
mongo_manager = MongoManager()
