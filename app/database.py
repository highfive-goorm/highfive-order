from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://root:mongodb_order@mongodb_order:27017")
db = client["order"]
order_collection = db["order"]


