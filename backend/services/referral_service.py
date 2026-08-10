"""Сервис реферальной системы"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db_models import Referral, Agent
from config import settings


class ReferralService:
    
    @staticmethod
    async def create_referral(session: AsyncSession, inviter_agent_id: int, invited_agent_id: int, level: int) -> Referral:
        existing = await session.execute(select(Referral).where(
            Referral.inviter_agent_id == inviter_agent_id, Referral.invited_agent_id == invited_agent_id))
        if existing.scalar_one_or_none():
            return existing.scalar_one_or_none()
        referral = Referral(inviter_agent_id=inviter_agent_id, invited_agent_id=invited_agent_id,
                           level=level, invited_turnover=0.0, total_bonus_earned=0.0)
        session.add(referral)
        await session.flush()
        return referral
    
    @staticmethod
    async def get_referrals_by_inviter(session: AsyncSession, inviter_agent_id: int, level: Optional[int] = None) -> List[Referral]:
        query = select(Referral).where(Referral.inviter_agent_id == inviter_agent_id)
        if level is not None: query = query.where(Referral.level == level)
        result = await session.execute(query.order_by(Referral.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_referral_stats(session: AsyncSession, agent_id: int) -> dict:
        l1 = list((await session.execute(select(Referral).where(Referral.inviter_agent_id == agent_id, Referral.level == 1))).scalars().all())
        l2 = list((await session.execute(select(Referral).where(Referral.inviter_agent_id == agent_id, Referral.level == 2))).scalars().all())
        l1_bonus = sum(r.total_bonus_earned or 0 for r in l1)
        l2_bonus = sum(r.total_bonus_earned or 0 for r in l2)
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        link = f"{settings.BASE_REFERRAL_URL}?start={agent.referral_code}" if agent else ""
        return {
            "referral_code": agent.referral_code if agent else "",
            "referral_link": link,
            "total_invited": len(l1) + len(l2),
            "level1_count": len(l1), "level2_count": len(l2),
            "total_bonus_earned": l1_bonus + l2_bonus,
            "level1_bonus": l1_bonus, "level2_bonus": l2_bonus,
            "level1_referrals": [{"id": r.invited_agent_id, "turnover": r.invited_turnover, "bonus": r.total_bonus_earned} for r in l1],
            "level2_referrals": [{"id": r.invited_agent_id, "turnover": r.invited_turnover, "bonus": r.total_bonus_earned} for r in l2],
        }