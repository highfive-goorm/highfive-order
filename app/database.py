from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://root:mongodb_order@mongodb_order:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client['order']

order_collection = db['order']
