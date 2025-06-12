# order/app/crud.py
from datetime import datetime

import os
import httpx
import requests
from bson import ObjectId
from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from starlette import status

from .database import collection

from .schemas import OrderCreate, OrderUpdate, OrderInDB # 스키마 임포트 변경

CART_BASE_URL = os.environ["CART_BASE_URL"]

def get_db() -> AsyncIOMotorCollection:
    return collection


class Crud:
    async def create_order(
            order_data: OrderCreate, # 입력 스키마: OrderCreate
            db_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        now = datetime.utcnow()
        # Pydantic v2: model_dump()
        doc_to_insert = order_data.model_dump(exclude_unset=True)
        doc_to_insert["created_at"] = now
        doc_to_insert["updated_at"] = now
        
        result = await db_collection.insert_one(doc_to_insert)
        # MongoDB가 생성한 _id를 포함하여 반환할 문서 조회
        created_doc = await db_collection.find_one({"_id": result.inserted_id})
        
        if order_data.is_from_cart and order_data.user_id:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"{CART_BASE_URL}/{order_data.user_id}",
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
        return created_doc

    async def get_orders(
            user_id: str = None,
            db_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        cursor = db_collection.find({"user_id": user_id})
        orders = await cursor.to_list(length=None)
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
        return doc

    async def update_order(
            id: str,
            order_update_payload: OrderUpdate, # 스키마 사용
            db_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        try:
            oid = ObjectId(id)
        except Exception:
            return None
        
        update_data_dict = order_update_payload.model_dump(exclude_unset=True)
        if not update_data_dict: # 업데이트할 내용이 없으면
            return await db_collection.find_one({"_id": oid}) # 현재 문서를 그대로 반환
            
        update_data_dict["updated_at"] = datetime.utcnow()
        await db_collection.update_one(
            {"_id": oid},
            {"$set": update_data_dict}
        )
        doc = await db_collection.find_one({"_id": oid})
        return doc

    async def delete_order(
            id: str,
            db_collection: AsyncIOMotorCollection = Depends(get_db)
    ):
        try:
            oid = ObjectId(id)
        except Exception:
            return {"deleted": 0}
        result = await db_collection.delete_one({"_id": oid})
        return {"deleted": result.deleted_count}
