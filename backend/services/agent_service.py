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
        full_name: str,
        max_user_id: int,
        phone: str,
        email: str,
        city: str,
        registration_type: RegistrationType,
        invited_by_agent_id: Optional[int] = None,
        referral_code: Optional[str] = None
    ) -> Agent:
        
        # Если referral_code не передан, генерируем на основе города и телефона
        if not referral_code:
            # Очищаем телефон от +7, 8 и других символов
            clean_phone = phone.replace('+7', '').replace('8', '').replace('+', '').replace('-', '').replace(' ', '').strip()
            # Если номер начинается с 7, тоже убираем
            if clean_phone.startswith('7'):
                clean_phone = clean_phone[1:]
            # Если номер начинается с 8, тоже убираем
            if clean_phone.startswith('8'):
                clean_phone = clean_phone[1:]
            
            # Определяем префикс по городу
            is_barnaul = city and 'барн' in city.lower()
            prefix = "V" if is_barnaul else "G"
            # Формируем referral_code = префикс + очищенный телефон
            referral_code = f"{prefix}{clean_phone}"
            
            # Проверяем уникальность кода
            existing = await session.execute(
                select(Agent).where(Agent.referral_code == referral_code)
            )
            if existing.scalar_one_or_none():
                # Если код занят, добавляем случайный суффикс
                import random
                suffix = ''.join(random.choices('0123456789', k=3))
                referral_code = f"{prefix}{clean_phone}_{suffix}"
        
        agent = Agent(
            max_user_id=max_user_id,
            full_name=full_name,
            phone=phone,  # Оригинальный номер сохраняем как есть
            email=email,
            city=city,
            registration_type=registration_type,
            status=AgentStatus.ACTIVE,
            referral_code=referral_code,
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