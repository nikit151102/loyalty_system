"""Роутер статистики"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from auth import get_current_user, get_agent_by_user_id
from database import get_session
from models.db_models import Agent, Client, Purchase, Commission, Referral

router = APIRouter(prefix="/statistics", tags=["statistics"])

@router.get("/me")
async def get_my_stats(payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    
    total_commission = float((await session.execute(select(func.coalesce(func.sum(Commission.amount), 0.0)).where(Commission.agent_id == agent.id))).scalar())
    total_clients = (await session.execute(select(func.count(Client.id)).where(Client.agent_id == agent.id))).scalar() or 0
    total_purchases = float((await session.execute(select(func.coalesce(func.sum(Purchase.amount), 0.0)).where(Purchase.agent_id == agent.id))).scalar())
    total_referrals = (await session.execute(select(func.count(Referral.id)).where(Referral.inviter_agent_id == agent.id))).scalar() or 0
    avg_rate = float((await session.execute(select(func.coalesce(func.avg(Commission.rate), 0.0)).where(Commission.agent_id == agent.id, Commission.referral_level == 0))).scalar())
    
    rate_dist = await session.execute(select(Commission.rate, func.count(Commission.id)).where(Commission.agent_id == agent.id, Commission.referral_level == 0).group_by(Commission.rate))
    commission_by_rate = {f"{int(rate*100)}%": count for rate, count in rate_dist.all()}
    
    top = (await session.execute(select(Client).where(Client.agent_id == agent.id).order_by(Client.total_purchases_amount.desc()).limit(5))).scalars().all()
    top_clients = [{"id": c.id, "full_name": c.full_name, "phone": c.phone, "total_purchases_amount": c.total_purchases_amount or 0, "purchases_count": c.purchases_count or 0} for c in top]
    
    monthly = (await session.execute(select(func.date_trunc("month", Commission.created_at), func.sum(Commission.amount)).where(Commission.agent_id == agent.id).group_by(func.date_trunc("month", Commission.created_at)).order_by(func.date_trunc("month", Commission.created_at).desc()).limit(12))).all()
    monthly_earnings = [{"month": m.strftime("%Y-%m") if m else None, "amount": float(a or 0)} for m, a in monthly]
    
    l1 = (await session.execute(select(func.count(Referral.id)).where(Referral.inviter_agent_id == agent.id, Referral.level == 1))).scalar() or 0
    l2 = (await session.execute(select(func.count(Referral.id)).where(Referral.inviter_agent_id == agent.id, Referral.level == 2))).scalar() or 0
    
    return {
        "agent_id": agent.id, "total_commission_earned": total_commission, "balance": agent.balance,
        "total_clients": total_clients, "total_purchases_amount": total_purchases, "total_referrals": total_referrals,
        "level1_referrals": l1, "level2_referrals": l2, "average_commission_rate": avg_rate,
        "commission_by_rate": commission_by_rate, "top_clients": top_clients, "monthly_earnings": monthly_earnings,
    }