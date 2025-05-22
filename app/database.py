# order/app/database.py
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://postgres:han00719()@mongodb_order:27017")
db = client["order"]
order_collection = db["order"]
