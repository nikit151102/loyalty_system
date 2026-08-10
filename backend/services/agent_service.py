"""Сервис агентов"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shortuuid
from models.db_models import Agent, AgentStatus, RegistrationType
from auth import get_agent_by_user_id


class AgentService:
    
    @staticmethod
    async def create_agent(
        session: AsyncSession,
        max_user_id: int,
        phone: str,
        email: str,
        city: str,
        registration_type: RegistrationType,
        invited_by_agent_id: Optional[int] = None,
        referral_code: Optional[str] = None  # НОВЫЙ ПАРАМЕТР
    ) -> Agent:
        
        # Если referral_code не передан, генерируем стандартный
        if not referral_code:
            referral_code = await AgentService.generate_referral_code(session)
        
        agent = Agent(
            max_user_id=max_user_id,
            phone=phone,
            email=email,
            city=city,
            registration_type=registration_type,
            status=AgentStatus.ACTIVE,
            referral_code=referral_code,  # ИСПОЛЬЗУЕМ ПЕРЕДАННЫЙ КОД
            invited_by_agent_id=invited_by_agent_id,
            balance=0.0,
            total_clients=0,
            total_purchases_amount=0.0,
            total_commission_earned=0.0,
            total_referrals_count=0
        )
        
        session.add(agent)
        await session.flush()
        
        return agent
    
    @staticmethod
    async def generate_referral_code(session: AsyncSession) -> str:
        """Генерация уникального реферального кода (стандартный метод)"""
        import secrets
        while True:
            code = secrets.token_hex(4).upper()
            existing = await session.execute(select(Agent).where(Agent.referral_code == code))
            if not existing.scalar_one_or_none():
                return code
    
    @staticmethod
    async def get_agent_by_id(session: AsyncSession, agent_id: int) -> Optional[Agent]:
        result = await session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_agent_by_referral_code(session: AsyncSession, code: str) -> Optional[Agent]:
        result = await session.execute(select(Agent).where(Agent.referral_code == code))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_agents(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[Agent]:
        result = await session.execute(select(Agent).offset(skip).limit(limit).order_by(Agent.created_at.desc()))
        return list(result.scalars().all())