"""Роутер заявок"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from auth import verify_api_key, get_agent_by_user_id
from database import get_session
from models.schemas import AgentRegisterRequest, ApplicationResponse, MessageResponse
from services.application_service import ApplicationService
from models.db_models import RegistrationType
from sqlalchemy import select
from models.db_models import Application

router = APIRouter(prefix="/applications", tags=["applications"])

@router.post("/register", response_model=ApplicationResponse)
async def register_agent(data: AgentRegisterRequest, session: AsyncSession = Depends(get_session)):
    try:
        existing = await get_agent_by_user_id(data.max_user_id, session)
        if existing: raise HTTPException(status_code=400, detail="Вы уже являетесь агентом")
        app = await ApplicationService.create_application(session, data.max_user_id, data.phone, data.email, data.city, RegistrationType(data.registration_type))
        return ApplicationResponse.model_validate(app)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register/{referral_code}", response_model=ApplicationResponse)
async def register_with_referral(referral_code: str, data: AgentRegisterRequest, session: AsyncSession = Depends(get_session)):
    try:
        existing = await get_agent_by_user_id(data.max_user_id, session)
        if existing: raise HTTPException(status_code=400, detail="Вы уже являетесь агентом")
        app = await ApplicationService.create_application(session, data.max_user_id, data.phone, data.email, RegistrationType(data.registration_type), referral_code)
        return ApplicationResponse.model_validate(app)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pending", response_model=List[ApplicationResponse], dependencies=[Depends(verify_api_key)])
async def list_pending(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), session: AsyncSession = Depends(get_session)):
    apps, _ = await ApplicationService.get_pending_applications(session, skip, limit)
    return [ApplicationResponse.model_validate(a) for a in apps]

@router.get("/all", response_model=List[ApplicationResponse], dependencies=[Depends(verify_api_key)])
async def list_all(status: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), session: AsyncSession = Depends(get_session)):
    from models.db_models import ApplicationStatus as AS
    apps, _ = await ApplicationService.get_all_applications(session, AS(status) if status else None, skip, limit)
    return [ApplicationResponse.model_validate(a) for a in apps]

@router.get("/{application_id}", response_model=ApplicationResponse, dependencies=[Depends(verify_api_key)])
async def get_app(application_id: int, session: AsyncSession = Depends(get_session)):
    from models.db_models import Application
    from sqlalchemy import select
    app = (await session.execute(select(Application).where(Application.id == application_id))).scalar_one_or_none()
    if not app: raise HTTPException(status_code=404, detail="Заявка не найдена")
    return ApplicationResponse.model_validate(app)

@router.patch("/{application_id}/approve", response_model=MessageResponse, dependencies=[Depends(verify_api_key)])
async def approve(application_id: int, reviewed_by: int = Query(...), session: AsyncSession = Depends(get_session)):
    try:
        agent = await ApplicationService.approve_application(session, application_id, reviewed_by)
        return MessageResponse(message=f"Одобрено. Агент ID: {agent.id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{application_id}/reject", response_model=MessageResponse, dependencies=[Depends(verify_api_key)])
async def reject(application_id: int, reviewed_by: int = Query(...), rejection_reason: Optional[str] = Query(None), session: AsyncSession = Depends(get_session)):
    try:
        await ApplicationService.reject_application(session, application_id, reviewed_by, rejection_reason)
        return MessageResponse(message="Отклонено")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user/{max_user_id}", dependencies=[Depends(verify_api_key)])
async def get_by_user(max_user_id: int, session: AsyncSession = Depends(get_session)):
    app = await ApplicationService.get_application_by_user(session, max_user_id)
    return ApplicationResponse.model_validate(app) if app else None


@router.get("/by-phone/{phone}")
async def by_phone(phone: str, session: AsyncSession = Depends(get_session)):
    application = (await session.execute(select(Application).where(Application.phone == phone))).scalar_one_or_none()
    return ApplicationResponse.model_validate(application) if application else None
