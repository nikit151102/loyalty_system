"""Роутер агентов"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from auth import get_current_user, verify_api_key, get_agent_by_user_id
from database import get_session
from models.schemas import AgentResponse, AgentStatusResponse
from services.agent_service import AgentService
from services.application_service import ApplicationService
from models.db_models import ApplicationStatus

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/me", response_model=AgentResponse)
async def get_my_profile(payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=404, detail="Агент не найден")
    return AgentResponse.model_validate(agent)

@router.get("/me/status", response_model=AgentStatusResponse)
async def get_my_status(payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    uid = int(payload.get("sub"))
    agent = await get_agent_by_user_id(uid, session)
    if agent:
        return AgentStatusResponse(status=agent.status.value, agent_id=agent.id, is_approved=True)
    app = await ApplicationService.get_application_by_user(session, uid)
    if not app: raise HTTPException(status_code=404, detail="Нет агента или заявки")
    return AgentStatusResponse(status=app.status.value, is_approved=app.status == ApplicationStatus.APPROVED,
                              rejection_reason=app.rejection_reason if app.status == ApplicationStatus.REJECTED else None)

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await AgentService.get_agent_by_id(session, agent_id)
    if not agent: raise HTTPException(status_code=404, detail="Агент не найден")
    return AgentResponse.model_validate(agent)

@router.get("/", response_model=List[AgentResponse], dependencies=[Depends(verify_api_key)])
async def list_agents(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_session)):
    agents = await AgentService.get_all_agents(session, skip, limit)
    return [AgentResponse.model_validate(a) for a in agents]

@router.get("/by-referral/{referral_code}", dependencies=[Depends(verify_api_key)])
async def get_agent_by_referral_code(
    referral_code: str,
    session: AsyncSession = Depends(get_session)
):
    """Получить агента по реферальному коду (для бота)"""
    from services.agent_service import AgentService
    
    agent = await AgentService.get_agent_by_referral_code(session, referral_code)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент с таким кодом не найден")
    
    return {
        "id": agent.id,
        "max_user_id": agent.max_user_id,
        "referral_code": agent.referral_code,
        "status": agent.status.value if hasattr(agent.status, "value") else agent.status,
        "total_clients": agent.total_clients,
    }



@router.get("/by-phone/{phone}", dependencies=[Depends(verify_api_key)])
async def get_agent_by_phone(phone: str, session: AsyncSession = Depends(get_session)):
    """Поиск агента по номеру телефона"""
    from sqlalchemy import select
    from models.db_models import Agent
    
    agent = (await session.execute(
        select(Agent).where(Agent.phone == phone)
    )).scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    
    return {
        "id": agent.id,
        "max_user_id": agent.max_user_id,
        "phone": agent.phone,
        "email": agent.email,
        "status": agent.status.value if hasattr(agent.status, "value") else agent.status,
        "referral_code": agent.referral_code,
    }