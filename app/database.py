import os

from motor.motor_asyncio import AsyncIOMotorClient

DB_USER = os.getenv("DB_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_URI = f"mongodb://{DB_USER}:{MONGO_PASSWORD}//@mongodb_order:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client['order']

order_collection = db['order']
