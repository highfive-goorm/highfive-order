# oder/app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from bson import ObjectId # ObjectId 임포트
from pydantic_core import core_schema # Pydantic v2
from pydantic.json_schema import JsonSchemaValue # Pydantic v2

# Pydantic v2 호환 PyObjectId 클래스 (promotion/app/schemas.py 참고)
class PyObjectId(ObjectId):
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError(f"'{v}' is not a valid ObjectId.")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_obj: core_schema.CoreSchema, handler) -> JsonSchemaValue:
        return {'type': 'string', 'format': 'objectid'}

class OrderItem(BaseModel):
    product_id: Optional[int]
    quantity: int
    discounted_price: Optional[int] = None
    discount: Optional[int] = None
    img_url: Optional[str] = None
    name: Optional[str] = None
    price: Optional[int] = None
    model_config = ConfigDict(from_attributes=True) # Pydantic v2 스타일

class OrderBase(BaseModel): # 공통 필드
    user_id: Optional[str]
    status: Literal["paid", "shipping", "shipped", "cancelled"]
    order_items: List[OrderItem]
    is_from_cart: bool
    total_price: Optional[int]

class OrderCreate(OrderBase): # API를 통해 새 주문 생성 시 요청 본문
    # id, created_at, updated_at는 클라이언트가 보내지 않음 (서버 생성)
    pass

class OrderUpdate(BaseModel): # 주문 업데이트 시 요청 본문
    status: Optional[Literal["paid", "shipping", "shipped", "cancelled"]] = None
    # 필요에 따라 다른 업데이트 가능한 필드 추가
    order_items: Optional[List[OrderItem]] = None
    is_from_cart: Optional[bool] = None
    total_price: Optional[int] = None

class OrderInDB(OrderBase): # DB 저장 형태 및 API 응답용 스키마
    id: PyObjectId = Field(..., alias="_id") # MongoDB _id를 id 필드로 매핑
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(
        populate_by_name=True, # alias (_id <-> id) 동작
        from_attributes=True,  # ORM 모드 대체 (Pydantic v2)
        json_encoders={ObjectId: str, datetime: lambda dt: dt.isoformat()} # datetime을 ISO 문자열로
    )