# order/app/crud.py
from datetime import datetime

import requests
from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from .database import order_collection

from .schemas import OrderCreate

def get_db()-> AsyncIOMotorCollection:
    return order_collection
class Crud:
    async def create_order(
            order: OrderCreate,
            collection: AsyncIOMotorCollection=Depends(get_db())

    ):
        now = datetime.utcnow()
        doc = order.dict(exclude_unset=True)
        doc.update({
            "created_at": now,
            "updated_at": now,
        })
        result = await collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        requests.delete(url=f'http://cart:8002/cart/{order.user_id}')
        return doc

    async def get_orders(
            user_id: str = None,
            collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        cursor = collection.find({"user_id": user_id})
        orders = await cursor.to_list(length=None)
        if collection is None:
            raise Exception({"message":"No Orders"})
        async for doc in cursor:
            orders.append(doc)
        return orders

    async def get_order(
            id: str,
            collection: AsyncIOMotorCollection = Depends(get_db)
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
            id: str,
            update_data: dict,
            collection: AsyncIOMotorCollection=Depends(get_db)

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
