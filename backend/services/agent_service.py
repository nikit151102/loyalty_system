"""Сервис агентов"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shortuuid
from models.db_models import Agent, AgentStatus, RegistrationType
from auth import get_agent_by_user_id


class AgentService:
    
    @staticmethod
    async def create_agent(session: AsyncSession, max_user_id: int, phone: str, email: str,
                          registration_type: RegistrationType, invited_by_agent_id: Optional[int] = None) -> Agent:
        existing = await get_agent_by_user_id(max_user_id, session)
        if existing: return existing
        referral_code = shortuuid.uuid()[:10].upper()
        agent = Agent(
            max_user_id=max_user_id, phone=phone, email=email,
            registration_type=registration_type, status=AgentStatus.ACTIVE,
            referral_code=referral_code, invited_by_agent_id=invited_by_agent_id,
            balance=0.0, total_clients=0, total_purchases_amount=0.0,
            total_commission_earned=0.0, total_referrals_count=0,
        )
        session.add(agent)
        await session.flush()
        return agent
    
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