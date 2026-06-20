"""MongoDB connection and index management."""
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import get_settings

client: AsyncIOMotorClient | None = None
db = None

async def connect_to_mongo():
    global client, db
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    await db.command("ping")
    await ensure_indexes(db)
    return db

async def close_mongo_connection():
    global client
    if client:
        client.close()

async def ensure_indexes(database):
    await database.users.create_index("email", unique=True)
    await database.clients.create_index("owner_user_id")
    await database.contracts.create_index("owner_user_id")
    await database.contracts.create_index("client_id")
    await database.analyses.create_index("contract_id")
    await database.chat_sessions.create_index("contract_id")
    await database.benchmarks.create_index("contract_id")


def get_database():
    if db is None:
        raise RuntimeError("Database is not connected")
    return db
