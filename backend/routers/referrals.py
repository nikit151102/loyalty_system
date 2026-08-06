"""Роутер рефералов"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from auth import get_current_user, get_agent_by_user_id
from database import get_session
from services.referral_service import ReferralService

router = APIRouter(prefix="/referrals", tags=["referrals"])

@router.get("/me")
async def my_referral(payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    return await ReferralService.get_referral_stats(session, agent.id)