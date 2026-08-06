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