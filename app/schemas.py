# oder/app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: int

class OrderBase(BaseModel):
    id: Optional[str] = None
    user_id: str
    status: Literal["paid", "shipping", "shipped", "cancelled"]
    order_items: List[OrderItem]
    total_price: int

class OrderCreate(OrderBase):
    pass

class OrderInDB(OrderBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        validate_by_name=True,
        from_attributes=True
    )