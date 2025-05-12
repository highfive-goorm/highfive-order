from fastapi import APIRouter, HTTPException
from datetime import datetime

from .database import order_collection
from .schemas import OrderCreate, OrderInDB

router = APIRouter(prefix="/order", tags=["Order"])


def serialize_order(order) -> dict:
    order["id"] = str(order["id"])
    del order["id"]
    return order


@router.post("/", response_model=OrderInDB)
async def create_order(order: OrderCreate):
    now = datetime.utcnow()
    doc = order.dict()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await order_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_order(doc)


@router.get("/{id}", response_model=OrderInDB)
async def get_order(id: int):
    order = await order_collection.find_one({"id":id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(order)


@router.put("/{id}", response_model=OrderInDB)
async def update_order(id: int, order: OrderCreate):
    doc = order.dict()
    doc["updated_at"] = datetime.utcnow()
    result = await order_collection.update_one(
        {"id": id},
        {"$set": doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    updated = await order_collection.find_one({"id": id})
    return serialize_order(updated)


@router.delete("/{id}")
async def delete_order(id: int):
    result = await order_collection.delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted"}
