from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from . import schemas


async def create_order(collection: AsyncIOMotorCollection, order: schemas.OrderCreate):
    now = datetime.utcnow()
    doc = order.dict()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await collection.insert_one(doc)
    return await collection.find_one({"id": result.inserted_id})


async def get_orders(collection: AsyncIOMotorCollection, user_id: int):
    cursor = collection.find({"user_id": user_id})
    orders = []
    async for doc in cursor:
        orders.append(doc)
    return orders


async def get_order(collection: AsyncIOMotorCollection, id: int):
    return await collection.find_one({"id": id})


async def update_order(collection: AsyncIOMotorCollection, id: int, update_data: dict):
    from bson import ObjectId
    update_data["updated_at"] = datetime.utcnow()
    await collection.update_one({"id": id}, {"$set": update_data})
    return await collection.find_one({"id": id})


async def delete_order(collection: AsyncIOMotorCollection, id:int):
    from bson import ObjectId
    result = await collection.delete_one({"id": id})
    return {"deleted": result.deleted_count}
