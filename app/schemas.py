# oder/app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class OrderItem(BaseModel):
    product_id: Optional[int]
    quantity: Optional[int]
    discounted_price: Optional[int]


class OrderBase(BaseModel):
    id: Optional[int]
    user_id: Optional[str]
    status: Literal["paid", "shipping", "shipped", "cancelled"]
    order_items: List[OrderItem]
    total_price: Optional[int]




class OrderInDB(OrderBase):
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True