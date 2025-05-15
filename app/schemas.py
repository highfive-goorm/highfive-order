from typing import List, Literal, Optional
from pydantic import BaseModel
from datetime import datetime

class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: int

class OrderBase(BaseModel):
    id: Optional[str] = None      # MongoDB PK (ObjectId)
    user_id: str                  # UUID (string)
    status: Literal["payed", "shipping", "shipped", "completed"]
    order_items: List[OrderItem]
    total_price: int

class OrderCreate(OrderBase):
    pass

class OrderInDB(OrderBase):
    created_at: datetime
    updated_at: datetime
