from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import schemas

async def create_order(
    collection: AsyncIOMotorCollection,
    order: schemas.OrderCreate,
    is_from_cart: bool = False
):
    now = datetime.utcnow()
    doc = order.dict(exclude_unset=True)
    doc.update({
        "created_at": now,
        "updated_at": now,
        "is_from_cart": is_from_cart
    })
    result = await collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc

async def get_orders(
    collection: AsyncIOMotorCollection,
    user_id: str = None
):
    query = {}
    if user_id:
        query["user_id"] = user_id
    cursor = collection.find(query)
    orders = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        orders.append(doc)
    return orders

async def get_order(
    collection: AsyncIOMotorCollection,
    id: str
):
    try:
        oid = ObjectId(id)
    except Exception:
        return None
    doc = await collection.find_one({"_id": oid})
    if doc:
        doc["id"] = str(doc["_id"])
    return doc

async def update_order(
    collection: AsyncIOMotorCollection,
    id: str,
    update_data: dict
):
    try:
        oid = ObjectId(id)
    except Exception:
        return None
    update_data["updated_at"] = datetime.utcnow()
    await collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    doc = await collection.find_one({"_id": oid})
    if doc:
        doc["id"] = str(doc["_id"])
    return doc

async def delete_order(
    collection: AsyncIOMotorCollection,
    id: str
):
    try:
        oid = ObjectId(id)
    except Exception:
        return {"deleted": 0}
    result = await collection.delete_one({"_id": oid})
    return {"deleted": result.deleted_count}
