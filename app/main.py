# order/app/main.py
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Path, Query
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId

from .database import collection
from .schemas import OrderInDB
from .crud import Crud as crud

app = FastAPI()

def get_db()-> AsyncIOMotorCollection:
    return collection
@app.post("/order", response_model=OrderInDB, status_code=201)
async def create_order(
        order: OrderInDB,
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    if order_collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 오류")
    doc = await crud.create_order(order, order_collection)
    return OrderInDB(**doc)


@app.get("/order/{user_id}", response_model=List[OrderInDB])
async def list_orders(
        user_id: Optional[str],
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    orders = await crud.get_orders(user_id, order_collection)
    return [OrderInDB(**doc) for doc in orders]


@app.put("/order/{id}", response_model=OrderInDB)
async def update_order(
        id: str,
        order: OrderInDB,
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    updated = await crud.update_order(id, order.dict(exclude_unset=True), order_collection)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderInDB(**updated)


@app.delete("/order/{id}", status_code=204)
async def delete_order(
        id: str,
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    result = await crud.delete_order(id, order_collection)
    if result.get("deleted", 0) == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return
