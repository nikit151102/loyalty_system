"""Роутер комиссий"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from auth import get_current_user, verify_api_key, get_agent_by_user_id
from database import get_session
from services.commission_service import CommissionService
from models.schemas import MessageResponse

router = APIRouter(prefix="/commissions", tags=["commissions"])

@router.get("/")
async def list_my_commissions(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    comms, total = await CommissionService.get_commissions_by_agent(session, agent.id, skip, limit)
    return {"items": [{"id": c.id, "amount": c.amount, "rate": c.rate, "referral_level": c.referral_level, "purchase_id": c.purchase_id, "created_at": c.created_at.isoformat() if c.created_at else None} for c in comms], "total": total}

@router.get("/transactions")
async def list_my_transactions(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    trans, total = await CommissionService.get_transactions_by_agent(session, agent.id, skip, limit)
    return {"items": [{"id": t.id, "type": t.transaction_type.value, "amount": t.amount, "description": t.description, "created_at": t.created_at.isoformat() if t.created_at else None} for t in trans], "total": total}

@router.post("/{agent_id}/withdraw", response_model=MessageResponse, dependencies=[Depends(verify_api_key)])
async def withdraw(agent_id: int, amount: float = Query(..., gt=0), session: AsyncSession = Depends(get_session)):
    try:
        await CommissionService.withdraw_balance(session, agent_id, amount)
        return MessageResponse(message=f"Выведено {amount} руб.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/adjust", response_model=MessageResponse, dependencies=[Depends(verify_api_key)])
async def adjust(agent_id: int, amount: float = Query(...), description: str = Query(...), session: AsyncSession = Depends(get_session)):
    try:
        await CommissionService.adjust_balance(session, agent_id, amount, description)
        return MessageResponse(message="Баланс скорректирован")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))