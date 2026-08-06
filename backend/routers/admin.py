"""Админ-роутер"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from auth import require_admin
from database import get_session
from models.db_models import Agent, Client, Application, Commission, Purchase, AgentStatus
from models.schemas import MessageResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats/overview")
async def overview(session: AsyncSession = Depends(get_session), _: dict = Depends(require_admin)):
    return {
        "total_agents": (await session.execute(select(func.count(Agent.id)))).scalar() or 0,
        "active_agents": (await session.execute(select(func.count(Agent.id)).where(Agent.status == "active"))).scalar() or 0,
        "total_clients": (await session.execute(select(func.count(Client.id)))).scalar() or 0,
        "total_purchases_amount": float((await session.execute(select(func.coalesce(func.sum(Purchase.amount), 0.0)))).scalar()),
        "total_commissions_paid": float((await session.execute(select(func.coalesce(func.sum(Commission.amount), 0.0)))).scalar()),
        "pending_applications": (await session.execute(select(func.count(Application.id)).where(Application.status == "pending"))).scalar() or 0,
    }

@router.get("/agents")
async def list_agents(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500), session: AsyncSession = Depends(get_session), _: dict = Depends(require_admin)):
    agents = (await session.execute(select(Agent).order_by(Agent.created_at.desc()).offset(skip).limit(limit))).scalars().all()
    total = (await session.execute(select(func.count(Agent.id)))).scalar() or 0
    return {"items": [{"id": a.id, "max_user_id": a.max_user_id, "phone": a.phone, "email": a.email,
                       "status": a.status.value if hasattr(a.status, "value") else a.status,
                       "registration_type": a.registration_type.value if hasattr(a.registration_type, "value") else a.registration_type,
                       "balance": a.balance, "total_clients": a.total_clients,
                       "total_commission_earned": a.total_commission_earned,
                       "created_at": a.created_at.isoformat() if a.created_at else None} for a in agents], "total": total}

@router.patch("/agents/{agent_id}/block")
async def block(agent_id: int, session: AsyncSession = Depends(get_session), _: dict = Depends(require_admin)):
    agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent: raise HTTPException(status_code=404, detail="Агент не найден")
    agent.status = AgentStatus.BLOCKED
    return MessageResponse(message=f"Агент {agent_id} заблокирован")

@router.patch("/agents/{agent_id}/activate")
async def activate(agent_id: int, session: AsyncSession = Depends(get_session), _: dict = Depends(require_admin)):
    agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent: raise HTTPException(status_code=404, detail="Агент не найден")
    agent.status = AgentStatus.ACTIVE
    return MessageResponse(message=f"Агент {agent_id} активирован")