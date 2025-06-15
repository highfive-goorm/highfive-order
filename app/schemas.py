# oder/app/schemas.py
from typing import List, Literal, Optional, Dict, Any
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
    status: Literal[
        "pending_payment", "paid", "shipping", "shipped", "cancelled",
        # Add any other order statuses you might use
    ]
    order_items: List[OrderItem]
    is_from_cart: bool
    total_price: Optional[int]
    # 카카오페이 관련 추가 정보 저장용 필드 (선택적)
    tid: Optional[str] = Field(None, description="카카오페이 거래 ID")
    payment_status: Optional[str] = Field("pending_payment", description="결제 상태")

class OrderCreate(OrderBase): # API를 통해 새 주문 생성 시 요청 본문
    # id, created_at, updated_at는 클라이언트가 보내지 않음 (서버 생성)
    # payment_status는 OrderBase에서 기본값을 가짐. 필요시 생성 시점에 명시적 설정 가능.
    pass

class OrderUpdate(BaseModel): # 주문 업데이트 시 요청 본문
    status: Optional[Literal["paid", "shipping", "shipped", "cancelled"]] = None
    order_items: Optional[List[OrderItem]] = None
    is_from_cart: Optional[bool] = None
    total_price: Optional[int] = None
    tid: Optional[str] = None
    payment_status: Optional[str] = None
    # 카카오페이 관련 추가 정보 업데이트용 필드 (선택적)
    # kakao_aid: Optional[str] = None
    # kakao_payment_method_type: Optional[str] = None
    # kakao_amount_details: Optional[Dict[str, Any]] = None

class OrderInDB(OrderBase): # DB 저장 형태 및 API 응답용 스키마
    id: PyObjectId = Field(..., alias="_id") # MongoDB _id를 id 필드로 매핑
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(
        populate_by_name=True, # alias (_id <-> id) 동작
        from_attributes=True,  # ORM 모드 대체 (Pydantic v2)
        json_encoders={ObjectId: str, datetime: lambda dt: dt.isoformat()} # datetime을 ISO 문자열로
    )

# --- KakaoPay Schemas ---
class KakaoPaymentReadyRequest(BaseModel):
    user_id: str # UUID string
    order_items: List[OrderItem]
    total_amount: int
    item_name: str # 예: "상품A 외 1건"
    is_from_cart: bool

class KakaoPaymentReadyResponse(BaseModel):
    next_redirect_pc_url: str
    # 선택적 필드 추가 (카카오페이 응답에 따라)
    # next_redirect_app_url: Optional[str] = None
    # next_redirect_mobile_url: Optional[str] = None
    # android_app_scheme: Optional[str] = None
    # ios_app_scheme: Optional[str] = None
    # created_at: Optional[datetime] = None # 카카오페이 응답의 created_at
    order_id: str # 생성된 주문의 MongoDB _id (string)

class KakaoPaymentApproveRequest(BaseModel):
    pg_token: str
    order_id: str # 결제 준비 시 생성된 주문의 MongoDB _id (string)

class KakaoAmountDetails(BaseModel): # 카카오페이 amount 상세 정보
    total: Optional[int] = None
    tax_free: Optional[int] = None
    vat: Optional[int] = None
    point: Optional[int] = None
    discount: Optional[int] = None
    green_deposit: Optional[int] = None

class KakaoPaymentApproveResponse(BaseModel):
    message: str
    order_id: str
    # payment_details를 더 구체적인 스키마로 변경하거나 Dict[str, Any] 유지
    payment_details: Optional[Dict[str, Any]] = Field(None, description="카카오페이 승인 전체 응답")
    # 또는 필요한 정보만 추출하여 별도 필드로 정의
    # aid: Optional[str] = None
    # tid: Optional[str] = None # 이미 order_id로 조회 가능
    # cid: Optional[str] = None
    # payment_method_type: Optional[str] = None
    # item_name: Optional[str] = None # 이미 주문 정보에 있음
    # quantity: Optional[int] = None # 이미 주문 정보에 있음
    # amount: Optional[KakaoAmountDetails] = None
    # approved_at: Optional[datetime] = None