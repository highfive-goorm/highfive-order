# order/app/main.py
from typing import List, Optional
import os
import httpx
from fastapi import FastAPI, HTTPException, Depends, Path, Query
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId
from starlette import status

from .database import collection
from .schemas import OrderInDB, OrderCreate, OrderUpdate # 스키마 임포트 변경
from .crud import Crud as crud

app = FastAPI()

PRODUCT_BASE_URL = os.environ["PRODUCT_BASE_URL"]
bulk_url = f"{PRODUCT_BASE_URL}/bulk"

def get_db() -> AsyncIOMotorCollection:
    return collection

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

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
