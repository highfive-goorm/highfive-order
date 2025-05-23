# oder/app/schemas.py
from typing import List, Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class OrderItem(BaseModel):
    product_id: Optional[int]
    quantity: int
    discounted_price: Optional[int] = None
    discount: Optional[int] = None
    img_url: Optional[str] = None
    name: Optional[str] = None
    price: Optional[int] = None


    class Config:
        orm_mode = True
class OrderBase(BaseModel):
    user_id: Optional[str]
    status: Literal["paid", "shipping", "shipped", "cancelled"]
    order_items: List[OrderItem]
    is_from_cart: bool
    total_price: Optional[int]




class OrderInDB(OrderBase):
    created_at: datetime=datetime.now(tz=ZoneInfo("Asia/Seoul"))
    updated_at: datetime=datetime.now(tz=ZoneInfo("Asia/Seoul"))
    class Config:
        orm_mode = True