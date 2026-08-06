"""Сервис заявок"""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.db_models import Application, ApplicationStatus, RegistrationType, Agent
from services.agent_service import AgentService
from services.referral_service import ReferralService


class ApplicationService:
    
    @staticmethod
    async def create_application(session: AsyncSession, max_user_id: int, phone: str, email: str,
                                registration_type: RegistrationType, referral_code: Optional[str] = None) -> Application:
        existing = await ApplicationService.get_pending_by_user(session, max_user_id)
        if existing: raise ValueError("Заявка уже на рассмотрении")
        application = Application(
            max_user_id=max_user_id, phone=phone, email=email,
            registration_type=registration_type, status=ApplicationStatus.PENDING,
        )
        session.add(application)
        await session.flush()
        if referral_code:
            application.rejection_reason = f"REF:{referral_code}"
        return application
    
    @staticmethod
    async def get_pending_by_user(session: AsyncSession, max_user_id: int) -> Optional[Application]:
        result = await session.execute(select(Application).where(
            Application.max_user_id == max_user_id, Application.status == ApplicationStatus.PENDING))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_application_by_user(session: AsyncSession, max_user_id: int) -> Optional[Application]:
        result = await session.execute(select(Application).where(
            Application.max_user_id == max_user_id).order_by(Application.created_at.desc()).limit(1))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_pending_applications(session: AsyncSession, skip: int = 0, limit: int = 50) -> Tuple[List[Application], int]:
        total = (await session.execute(select(func.count(Application.id)).where(Application.status == ApplicationStatus.PENDING))).scalar() or 0
        result = await session.execute(select(Application).where(Application.status == ApplicationStatus.PENDING).order_by(Application.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total
    
    @staticmethod
    async def get_all_applications(session: AsyncSession, status=None, skip: int = 0, limit: int = 50) -> Tuple[List[Application], int]:
        query = select(Application); count_query = select(func.count(Application.id))
        if status:
            query = query.where(Application.status == status)
            count_query = count_query.where(Application.status == status)
        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(query.order_by(Application.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total
    
    @staticmethod
    async def approve_application(session: AsyncSession, application_id: int, reviewed_by: int):
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()
        if not application: raise ValueError("Заявка не найдена")
        if application.status != ApplicationStatus.PENDING: raise ValueError("Заявка уже рассмотрена")
        
        invited_by_agent_id = None
        if application.rejection_reason and application.rejection_reason.startswith("REF:"):
            referral_code = application.rejection_reason[4:]
            inviter = await AgentService.get_agent_by_referral_code(session, referral_code)
            if inviter: invited_by_agent_id = inviter.id
        
        agent = await AgentService.create_agent(
            session=session, max_user_id=application.max_user_id, phone=application.phone,
            email=application.email, registration_type=application.registration_type,
            invited_by_agent_id=invited_by_agent_id)
        
        application.status = ApplicationStatus.APPROVED
        application.agent_id = agent.id
        application.reviewed_by = reviewed_by
        application.reviewed_at = datetime.utcnow()
        application.rejection_reason = None
        agent.approved_at = datetime.utcnow()
        
        # Реферальная связь 1 уровня
        if invited_by_agent_id:
            await ReferralService.create_referral(session, invited_by_agent_id, agent.id, 1)
            inviter = (await session.execute(select(Agent).where(Agent.id == invited_by_agent_id))).scalar_one_or_none()
            # Реферальная связь 2 уровня (если у пригласившего есть свой пригласивший)
            if inviter and inviter.invited_by_agent_id:
                await ReferralService.create_referral(session, inviter.invited_by_agent_id, agent.id, 2)
        
        await session.flush()
        return agent
    
    @staticmethod
    async def reject_application(session: AsyncSession, application_id: int, reviewed_by: int, rejection_reason: Optional[str] = None):
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()
        if not application: raise ValueError("Заявка не найдена")
        if application.status != ApplicationStatus.PENDING: raise ValueError("Заявка уже рассмотрена")
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = rejection_reason
        application.reviewed_by = reviewed_by
        application.reviewed_at = datetime.utcnow()
        await session.flush()
        return application