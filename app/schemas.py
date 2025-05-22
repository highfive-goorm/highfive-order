# oder/app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class OrderItem(BaseModel):
    product_id: Optional[int]
    quantity: Optional[int]
    price: Optional[int]


class OrderBase(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str]
    status: Literal["paid", "shipping", "shipped", "cancelled"]
    order_items: List[OrderItem]
    total_price: Optional[int]


class OrderCreate(OrderBase):
    pass


class OrderInDB(OrderBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
