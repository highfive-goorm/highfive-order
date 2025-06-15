# order/app/main.py
from typing import List, Optional
import os
import httpx
from fastapi import FastAPI, HTTPException, Depends, Path, Query
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId
from starlette import status
import json # json 모듈 임포트 추가

from .database import collection
from .schemas import (
    OrderInDB, OrderCreate, OrderUpdate,
    KakaoPaymentReadyRequest, KakaoPaymentReadyResponse,
    KakaoPaymentApproveRequest, KakaoPaymentApproveResponse
)
from .crud import Crud as crud

app = FastAPI()

PRODUCT_BASE_URL = os.environ["PRODUCT_BASE_URL"]
bulk_url = f"{PRODUCT_BASE_URL}/bulk"
KAKAO_ADMIN_KEY = os.getenv("KAKAO_ADMIN_KEY")
FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:3000") # 기본값 설정
KAKAO_API_BASE_URL = "https://open-api.kakaopay.com/online"

def get_db() -> AsyncIOMotorCollection:
    return collection

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# --- Helper for Kakao API calls ---
async def call_kakao_api(url: str, headers: dict, data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        response.raise_for_status() # HTTP 에러 시 예외 발생
        return response.json()

@app.post("/order", response_model=OrderInDB, status_code=201)
async def create_order(
        order_payload: OrderCreate, # 요청 본문 스키마: OrderCreate
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    if order_collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 오류")
    created_doc_dict = await crud.create_order(order_payload, order_collection)
    return OrderInDB.model_validate(created_doc_dict) # Pydantic v2 스타일


@app.get("/order/{user_id}", response_model=List[OrderInDB])
async def get_orders(
        user_id: str,
        order_collection: AsyncIOMotorCollection = Depends(get_db),
):
    # 0) 컬렉션 연결 확인
    if order_collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 연결 오류"
        )

    # 1) 해당 유저의 모든 주문 조회
    # orders = await order_collection.find({"user_id": user_id}).to_list() # crud 함수 사용
    orders = await crud.get_orders(user_id=user_id, db_collection=order_collection)
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # 2) 주문들에 포함된 모든 product_id 추출 (중복 제거)
    product_ids = {
        item["product_id"]
        for order in orders 
        for item in order.get("order_items", [])
    }

    # 3) 상품 서비스에 bulk 요청
    detailed_map: dict[str, dict] = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                bulk_url,
                json={"product_ids": list(product_ids)},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            # 반환이 list 인지, dict 인지 처리
            prods = data if isinstance(data, list) else data.get("products", [])
            for prod in prods:
                detailed_map[prod["id"]] = prod

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"상품 서비스 네트워크 오류: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"상품 서비스 처리 중 오류: {e}"
        )

    # 4) 각 주문 항목에 상품·브랜드 정보 결합
    enriched_orders = []
    for order in orders: 
        enriched_items = []
        for item in order.get("order_items", []): # order -> order_doc, get에 기본값 추가
            prod = detailed_map.get(item["product_id"], {})
            enriched_items.append({
                **item,
                # 원래 들어온 item["quantity"]를 그대로 유지해야 합니다
                "quantity": item["quantity"],
                # 상품 서비스에서 가져온 필드들만 덮어쓰기
                "name": prod.get("name", item.get("name")),
                "img_url": prod.get("img_url", item.get("img_url")),
                "discount": prod.get("discount", item.get("discount", 0)),
                "price": prod.get("price", item.get("price", 0)),
                "discounted_price": prod.get("discounted_price", item.get("discounted_price", 0)),
            })
        order["order_items"] = enriched_items 
        # OrderInDB.model_validate가 _id를 id로 alias 처리하므로 수동 변환 불필요
        enriched_orders.append(order) 
    return [OrderInDB.model_validate(o) for o in enriched_orders] # Pydantic v2


@app.put("/order/{id}", response_model=OrderInDB)
async def update_order(
        id: str, # ObjectId 문자열
        order_update_payload: OrderUpdate, # 요청 본문 스키마: OrderUpdate
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    updated_doc_dict = await crud.update_order(id, order_update_payload, order_collection)
    if not updated_doc_dict:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderInDB.model_validate(updated_doc_dict) # Pydantic v2


@app.delete("/order/{id}", status_code=204)
async def delete_order(
        id: str, # ObjectId 문자열
        order_collection: AsyncIOMotorCollection = Depends(get_db)
):
    result = await crud.delete_order(id, order_collection)
    if result.get("deleted", 0) == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return


@app.post("/payment/kakao/ready", response_model=KakaoPaymentReadyResponse, status_code=status.HTTP_200_OK)
async def kakao_payment_ready(
    payload: KakaoPaymentReadyRequest,
    db: AsyncIOMotorCollection = Depends(get_db)
):
    if not KAKAO_ADMIN_KEY:
        raise HTTPException(status_code=500, detail="카카오 어드민 키가 설정되지 않았습니다.")

    # 1. Create Order document
    order_create_data = OrderCreate(
        user_id=payload.user_id,
        order_items=payload.order_items,
        total_price=payload.total_amount, # total_price로 매핑
        is_from_cart=payload.is_from_cart,
        status="pending_payment", # 초기 주문 상태
        payment_status="pending_kakao_ready" # 초기 결제 상태
    )
    created_order_doc = await crud.create_order(order_create_data, db)
    order_id_str = str(created_order_doc["_id"])

    # 2. Prepare KakaoPay "ready" API call
    kakao_ready_url = f"{KAKAO_API_BASE_URL}/v1/payment/ready"
    headers = {
        # 공식 문서에 따라 SECRET_KEY 사용 (KAKAO_ADMIN_KEY 환경 변수에 결제용 Secret Key 저장 필요)
        "Authorization": f"SECRET_KEY {KAKAO_ADMIN_KEY}",
        "Content-type": "application/json",
    }

    # order_items에서 총 수량 계산
    total_quantity = sum(item.quantity for item in payload.order_items)

    approval_url_base = f"{FRONTEND_DOMAIN}/pay/approve"
    cancel_url_base = f"{FRONTEND_DOMAIN}/pay/cancel"
    fail_url_base = f"{FRONTEND_DOMAIN}/pay/fail"

    kakao_payload = {
        "cid": "TC0ONETIME", # 테스트용 CID
        "partner_order_id": order_id_str,
        "partner_user_id": payload.user_id,
        "item_name": payload.item_name,
        "quantity": total_quantity, # Integer 타입으로 전달
        "total_amount": payload.total_amount, # Integer 타입으로 전달
        "vat_amount": 0, # Integer 타입으로 전달 (필요시 실제 부가세 계산 로직 추가)
        "tax_free_amount": 0,
        "approval_url": f"{approval_url_base}?order_id={order_id_str}",
        "cancel_url": f"{cancel_url_base}?order_id={order_id_str}",
        "fail_url": f"{fail_url_base}?order_id={order_id_str}",
    }

    try:
        kakao_response = await call_kakao_api(kakao_ready_url, headers, json.dumps(kakao_payload)) # json.dumps로 직렬화
    except httpx.HTTPStatusError as e:
        await crud.update_order(order_id_str, OrderUpdate(payment_status="failed_kakao_ready"), db)
        raise HTTPException(status_code=e.response.status_code, detail=f"카카오페이 준비 요청 실패: {e.response.text}")
    except Exception as e:
        await crud.update_order(order_id_str, OrderUpdate(payment_status="failed_kakao_ready"), db)
        raise HTTPException(status_code=500, detail=f"카카오페이 준비 중 오류: {str(e)}")

    tid = kakao_response.get("tid")
    next_redirect_pc_url = kakao_response.get("next_redirect_pc_url")
    # 추가 응답 필드 (선택적 저장)
    # next_redirect_app_url = kakao_response.get("next_redirect_app_url")
    # next_redirect_mobile_url = kakao_response.get("next_redirect_mobile_url")
    # android_app_scheme = kakao_response.get("android_app_scheme")
    # ios_app_scheme = kakao_response.get("ios_app_scheme")
    # kakao_created_at = kakao_response.get("created_at")

    if not tid or not next_redirect_pc_url:
        await crud.update_order(order_id_str, OrderUpdate(payment_status="failed_kakao_ready_response"), db)
        raise HTTPException(status_code=500, detail="카카오페이 응답에서 tid 또는 URL을 받지 못했습니다.")

    # 3. Update Order document with tid
    update_fields = OrderUpdate(tid=tid, payment_status="ready_kakao")
    # 예시: if kakao_created_at: update_fields.kakao_payment_created_at = kakao_created_at (스키마에 필드 추가 필요)
    await crud.update_order(order_id_str, update_fields, db)


    return KakaoPaymentReadyResponse(
        next_redirect_pc_url=next_redirect_pc_url,
        order_id=order_id_str
    )

@app.post("/payment/kakao/approve", response_model=KakaoPaymentApproveResponse, status_code=status.HTTP_200_OK)
async def kakao_payment_approve(
    payload: KakaoPaymentApproveRequest,
    db: AsyncIOMotorCollection = Depends(get_db)
):
    if not KAKAO_ADMIN_KEY:
        raise HTTPException(status_code=500, detail="카카오 어드민 키가 설정되지 않았습니다.")

    # 1. Retrieve order and tid
    order_doc = await crud.get_order(payload.order_id, db)
    if not order_doc:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
    
    tid = order_doc.get("tid")
    if not tid:
        raise HTTPException(status_code=404, detail="거래 ID(tid)가 주문에 없습니다. 결제 준비를 다시 시도해주세요.")

    # 2. Prepare KakaoPay "approve" API call
    kakao_approve_url = f"{KAKAO_API_BASE_URL}/v1/payment/approve"
    headers = {
        # 공식 문서에 따라 SECRET_KEY 사용
        "Authorization": f"SECRET_KEY {KAKAO_ADMIN_KEY}",
        "Content-type": "application/json",
    }
    kakao_payload = {
        "cid": "TC0ONETIME",
        "tid": tid,
        "partner_order_id": payload.order_id,
        "partner_user_id": order_doc.get("user_id"),
        "pg_token": payload.pg_token,
    }

    try:
        kakao_response = await call_kakao_api(kakao_approve_url, headers, json.dumps(kakao_payload))
    except httpx.HTTPStatusError as e:
        await crud.update_order(payload.order_id, OrderUpdate(payment_status="failed_kakao_approve"), db)
        raise HTTPException(status_code=e.response.status_code, detail=f"카카오페이 승인 요청 실패: {e.response.text}")
    except Exception as e:
        await crud.update_order(payload.order_id, OrderUpdate(payment_status="failed_kakao_approve"), db)
        raise HTTPException(status_code=500, detail=f"카카오페이 승인 중 오류: {str(e)}")

    # 3. Update Order document
    # 카카오페이 응답에서 추가 정보 추출 (선택적)
    aid = kakao_response.get("aid")
    payment_method_type = kakao_response.get("payment_method_type")
    amount_details = kakao_response.get("amount")
    # approved_at_str = kakao_response.get("approved_at")

    update_fields = OrderUpdate(status="paid", payment_status="paid_kakao")
    # 예시: if aid: update_fields.kakao_aid = aid (스키마에 필드 추가 필요)
    await crud.update_order(payload.order_id, update_fields, db)

    return KakaoPaymentApproveResponse(
        message="Payment successful",
        order_id=payload.order_id,
        payment_details=kakao_response # 전체 응답을 전달하거나 필요한 부분만 추출
    )
