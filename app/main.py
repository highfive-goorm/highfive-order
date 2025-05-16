# order/app/main.py
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Path, Query
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId

from .schemas import OrderInDB, OrderBase, OrderCreate
from . import crud

app = FastAPI()

def get_db() -> AsyncIOMotorCollection:
    client = AsyncIOMotorClient("mongodb://root:mongodb_order@mongodb_order:27017")
    return client.order.order

@app.post("/order", response_model=OrderInDB, status_code=201)
async def create_order(
        order: OrderCreate,
        is_from_cart: Optional[bool] = Query(False, description="장바구니에서 주문 생성 여부"),
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    if collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 오류")
    doc = await crud.create_order(collection, order, is_from_cart=is_from_cart)
    return OrderInDB(**doc)

@app.get("/order", response_model=List[OrderInDB])
async def list_orders(
        user_id: Optional[str] = Query(None, description="조회할 유저 UUID"),
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    orders = await crud.get_orders(collection, user_id)
    return [OrderInDB(**doc) for doc in orders]

@app.get("/order/{id}", response_model=OrderInDB)
async def get_order(
        id: str,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    doc = await crud.get_order(collection, id)
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderInDB(**doc)

@app.put("/order/{id}", response_model=OrderInDB)
async def update_order(
        id: str,
        order: OrderCreate,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    updated = await crud.update_order(collection, id, order.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderInDB(**updated)

@app.delete("/order/{id}", status_code=204)
async def delete_order(
        id: str,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    result = await crud.delete_order(collection, id)
    if result.get("deleted", 0) == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return
