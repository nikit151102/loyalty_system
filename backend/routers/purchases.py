"""Роутер покупок"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select
from auth import get_current_user, verify_api_key
from database import get_session
from models.schemas import PurchaseCreateRequest, PurchaseResponse
from services.commission_service import CommissionService
from services.client_service import ClientService
from models.db_models import Purchase

router = APIRouter(prefix="/purchases", tags=["purchases"])

@router.post("/", response_model=PurchaseResponse)
async def create_purchase(data: PurchaseCreateRequest, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    client = await ClientService.get_client_by_id(session, data.client_id)
    if not client: raise HTTPException(status_code=404, detail="Клиент не найден")
    try:
        purchase = await CommissionService.create_purchase_and_commissions(session, data.client_id, data.amount, data.order_number, data.comment, data.added_by_user_id)
        return PurchaseResponse.model_validate(purchase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/external", response_model=PurchaseResponse, dependencies=[Depends(verify_api_key)])
async def create_purchase_external(data: PurchaseCreateRequest, session: AsyncSession = Depends(get_session)):
    try:
        purchase = await CommissionService.create_purchase_and_commissions(session, data.client_id, data.amount, data.order_number, data.comment, data.added_by_user_id)
        return PurchaseResponse.model_validate(purchase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/client/{client_id}", response_model=List[PurchaseResponse])
async def get_client_purchases(client_id: int, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Purchase).where(Purchase.client_id == client_id).order_by(Purchase.created_at.desc()).offset(skip).limit(limit))
    return [PurchaseResponse.model_validate(p) for p in result.scalars().all()]