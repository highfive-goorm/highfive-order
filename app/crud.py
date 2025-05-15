from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import schemas

async def create_order(
    collection: AsyncIOMotorCollection,
    order: schemas.OrderCreate
):
    now = datetime.utcnow()
    doc = order.dict()
    doc.update({
        "created_at": now,
        "updated_at": now
    })

    result = await collection.insert_one(doc)
    # 삽입된 _id를 문자열 id로 추가
    doc["id"] = str(result.inserted_id)
    return doc


async def get_orders(
    collection: AsyncIOMotorCollection,
    user_id: int
):
    cursor = collection.find({"user_id": user_id})
    orders = []
    async for doc in cursor:
        # ObjectId → 문자열 id
        doc["id"] = str(doc["_id"])
        orders.append(doc)
    return orders


async def get_order(
    collection: AsyncIOMotorCollection,
    id: str
):
    # 1) 유효한 ObjectId 변환
    try:
        oid = ObjectId(id)
    except Exception:
        return None

    # 2) 조회
    doc = await collection.find_one({"_id": oid})
    if doc:
        doc["id"] = str(doc["_id"])
    return doc


async def update_order(
    collection: AsyncIOMotorCollection,
    id: str,
    update_data: dict
):
    # 1) 유효한 ObjectId 변환
    try:
        oid = ObjectId(id)
    except Exception:
        return None

    # 2) 타임스탬프 갱신
    update_data["updated_at"] = datetime.utcnow()
    await collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )

    # 3) 갱신된 문서 조회 후 id 변환
    doc = await collection.find_one({"_id": oid})
    if doc:
        doc["id"] = str(doc["_id"])
    return doc


async def delete_order(
    collection: AsyncIOMotorCollection,
    id: str
):
    # 1) 유효한 ObjectId 변환
    try:
        oid = ObjectId(id)
    except Exception:
        return {"deleted": 0}

    # 2) 삭제
    result = await collection.delete_one({"_id": oid})
    return {"deleted": result.deleted_count}
