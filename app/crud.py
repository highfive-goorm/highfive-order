# order/app/crud.py
from datetime import datetime


import httpx
import requests
from bson import ObjectId
from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from starlette import status

from .database import collection

from .schemas import OrderInDB


def get_db() -> AsyncIOMotorCollection:
    return collection


class Crud:
    async def create_order(
            order: OrderInDB,
            order_collection: AsyncIOMotorCollection = Depends(get_db())

    ):
        now = datetime.utcnow()
        doc = order.dict(exclude_unset=True)
        doc.update({
            "created_at": now,
            "updated_at": now,
        })
        result = await order_collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        if order.is_from_cart:  # ← 콜론 필수!
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"http://cart:8002/cart/{order.user_id}",
                        timeout=5.0
                    )
                    resp.raise_for_status()
            except httpx.RequestError as e:
                # 네트워크 오류
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"장바구니 서비스 네트워크 오류: {e}"
                )
            except httpx.HTTPStatusError as e:
                # HTTP 오류(404/405 등)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"장바구니 삭제 실패: HTTP {e.response.status_code}"
                )
        return doc

    async def get_orders(
            user_id: str = None,
            order_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        cursor = order_collection.find({"user_id": user_id})
        orders = await cursor.to_list(length=None)
        if collection is None:
            raise Exception({"message": "No Orders"})
        async for doc in cursor:
            orders.append(doc)
        return orders

    async def get_order(
            id: str,
            order_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        try:
            oid = ObjectId(id)
        except Exception:
            return None
        doc = await order_collection.find_one({"_id": oid})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def update_order(
            id: str,
            update_data: dict,
            order_collection: AsyncIOMotorCollection = Depends(get_db)

    ):
        try:
            oid = ObjectId(id)
        except Exception:
            return None
        update_data["updated_at"] = datetime.utcnow()
        await order_collection.update_one(
            {"_id": oid},
            {"$set": update_data}
        )
        doc = await order_collection.find_one({"_id": oid})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def delete_order(
            id: str,
            order_collection: AsyncIOMotorCollection = Depends(get_db())

    ):
        try:
            oid = ObjectId(id)
        except Exception:
            return {"deleted": 0}
        result = await order_collection.delete_one({"_id": oid})
        return {"deleted": result.deleted_count}
