# main.py
from typing import List
from fastapi import FastAPI, HTTPException, Depends, Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId

from .schemas import OrderInDB, OrderBase

app = FastAPI()


def get_db() -> AsyncIOMotorCollection:
    """
    MongoDB에 연결하여 Order 컬렉션을 반환합니다.
    URI는 환경변수나 시크릿 매니저로 관리할 것을 권장합니다.
    """
    client = AsyncIOMotorClient("mongodb://root:mongodb_order@mongodb_order:27017")
    return client.order.order  # 'order' 데이터베이스의 'order' 컬렉션


@app.post(
    "/order/{is_from_cart}",
    response_model=OrderBase,
    status_code=201
)
async def create_order(
        is_from_cart: bool = Path(..., description="장바구니에서 주문 생성 여부"),
        order: OrderBase = ...,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    # 1) 컬렉션 연결 확인
    if collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 오류")

    # 2) 문서 데이터 생성
    now = datetime.utcnow()
    doc = order.dict()
    doc.update({
        "is_from_cart": is_from_cart,
        "created_at": now,
        "updated_at": now
    })

    result = await collection.insert_one(doc)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="DB 삽입 실패")

    # 3) 반환용 id 세팅
    doc["id"] = str(result.inserted_id)
    return OrderInDB(**doc)


@app.post("/order", response_model=OrderInDB, status_code=201)
async def create_order(
        order: OrderBase,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    # 1) 컬렉션 확인
    if collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 오류")

    # 2) 문서 생성
    now = datetime.utcnow()
    doc = order.dict()
    doc.update({
        "created_at": now,
        "updated_at": now
    })

    result = await collection.insert_one(doc)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="DB 삽입 실패")

    # 3) 반환용 id 추가
    doc["id"] = str(result.inserted_id)
    return OrderInDB(**doc)


@app.get("/order", response_model=List[OrderInDB])
async def list_orders(
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    orders: List[OrderInDB] = []
    async for doc in collection.find():
        doc["id"] = str(doc["_id"])
        orders.append(OrderInDB(**doc))
    return orders


@app.get("/order/{id}", response_model=OrderBase)
async def get_order(
        id: str,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    # 1) ObjectId 변환 검사
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 2) 문서 조회
    doc = await collection.find_one({"id": id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Order not found")


    return OrderBase(**doc)


@app.put("/order/{id}", response_model=OrderBase)
async def update_order(
        id: str,
        order: OrderBase,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    # 1) ObjectId 변환 검사
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 2) 업데이트 데이터 준비
    update_data = order.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    # 3) 업데이트 실행
    result = await collection.update_one({"_id": oid}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Order not found or nothing to update")

    # 4) 업데이트된 문서 반환
    updated = await collection.find_one({"_id": oid})
    updated["id"] = str(updated["_id"])
    return OrderInDB(**updated)


@app.delete("/order/{id}", status_code=204)
async def delete_order(
        id: str,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    # 1) ObjectId 변환 검사
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 2) 삭제 실행
    result = await collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return
