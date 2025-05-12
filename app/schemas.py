from typing import List, Literal, Optional
from pydantic import BaseModel
from datetime import datetime


class OrderItem(BaseModel):
    id: int
    quantity: int
    price: int


class OrderBase(BaseModel):
    user_id: int
    status: Literal["payed", "shipping", "shipped", "completed"]
    order_items: List[OrderItem]
    total_price: int


class OrderCreate(OrderBase):
    pass


class OrderInDB(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
