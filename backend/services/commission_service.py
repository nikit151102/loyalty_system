"""Сервис комиссий с 2-уровневой реферальной системой"""
from typing import Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.db_models import Commission, Purchase, Client, Agent, LoyaltyTransaction, TransactionType, Referral, AgentStatus
from config import settings


class CommissionService:
    
    @staticmethod
    def calculate_commission_rate(agent_turnover: float) -> float:
        return settings.COMMISSION_RATE_HIGH if agent_turnover > settings.COMMISSION_THRESHOLD else settings.COMMISSION_RATE_LOW
    
    @staticmethod
    async def calculate_agent_turnover(session: AsyncSession, agent_id: int) -> float:
        return float((await session.execute(select(func.coalesce(func.sum(Purchase.amount), 0.0)).where(Purchase.agent_id == agent_id))).scalar())
    
    @staticmethod
    async def create_purchase_and_commissions(session: AsyncSession, client_id: int, amount: float,
                                             order_number=None, comment=None, added_by_user_id=None) -> Purchase:
        client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
        if not client: raise ValueError("Клиент не найден")
        agent = (await session.execute(select(Agent).where(Agent.id == client.agent_id))).scalar_one_or_none()
        if not agent: raise ValueError("Агент не найден")
        
        turnover = await CommissionService.calculate_agent_turnover(session, agent.id)
        rate = CommissionService.calculate_commission_rate(turnover + amount)
        commission_amount = amount * rate
        
        # Создаём покупку
        purchase = Purchase(client_id=client_id, agent_id=agent.id, amount=amount,
                          order_number=order_number, comment=comment, added_by_user_id=added_by_user_id,
                          commission_amount=commission_amount, commission_rate=rate)
        session.add(purchase)
        await session.flush()
        
        # Прямая комиссия агенту
        main_comm = Commission(agent_id=agent.id, purchase_id=purchase.id, amount=commission_amount, rate=rate, referral_level=0)
        session.add(main_comm)
        
        main_trans = LoyaltyTransaction(agent_id=agent.id, transaction_type=TransactionType.ACCRUAL,
                                       amount=commission_amount, description=f"Комиссия {int(rate*100)}% от покупки {client.full_name}",
                                       commission_id=main_comm.id, purchase_id=purchase.id)
        session.add(main_trans)
        
        agent.balance = (agent.balance or 0) + commission_amount
        agent.total_commission_earned = (agent.total_commission_earned or 0) + commission_amount
        agent.total_purchases_amount = (agent.total_purchases_amount or 0) + amount
        client.total_purchases_amount = (client.total_purchases_amount or 0) + amount
        client.purchases_count = (client.purchases_count or 0) + 1
        
        # === РЕФЕРАЛЬНАЯ СИСТЕМА 2 УРОВНЯ ===
        l1_bonus, l2_bonus = 0.0, 0.0
        
        # Уровень 1: если агент был приглашён другим агентом
        if agent.invited_by_agent_id:
            ref1 = (await session.execute(select(Referral).where(
                Referral.inviter_agent_id == agent.invited_by_agent_id,
                Referral.invited_agent_id == agent.id, Referral.level == 1))).scalar_one_or_none()
            if ref1:
                inviter = (await session.execute(select(Agent).where(Agent.id == agent.invited_by_agent_id))).scalar_one_or_none()
                if inviter and inviter.status == AgentStatus.ACTIVE:
                    # 50% от комиссии
                    l1_bonus = commission_amount * 0.5
                    ref1.invited_turnover = (ref1.invited_turnover or 0) + amount
                    ref1.total_bonus_earned = (ref1.total_bonus_earned or 0) + l1_bonus
                    comm1 = Commission(agent_id=inviter.id, purchase_id=purchase.id, amount=l1_bonus, rate=rate, referral_level=1)
                    session.add(comm1)
                    trans1 = LoyaltyTransaction(agent_id=inviter.id, transaction_type=TransactionType.REFERRAL_BONUS,
                                               amount=l1_bonus, description=f"Реферальный бонус 1 уровня",
                                               commission_id=comm1.id, purchase_id=purchase.id)
                    session.add(trans1)
                    inviter.balance = (inviter.balance or 0) + l1_bonus
                    inviter.total_commission_earned = (inviter.total_commission_earned or 0) + l1_bonus
                    
                    # Уровень 2: агент пригласившего пригласившего
                    if inviter.invited_by_agent_id:
                        ref2 = (await session.execute(select(Referral).where(
                            Referral.inviter_agent_id == inviter.invited_by_agent_id,
                            Referral.invited_agent_id == agent.id, Referral.level == 2))).scalar_one_or_none()
                        if ref2:
                            inviter2 = (await session.execute(select(Agent).where(Agent.id == inviter.invited_by_agent_id))).scalar_one_or_none()
                            if inviter2 and inviter2.status == AgentStatus.ACTIVE:
                                # 25% от комиссии
                                l2_bonus = commission_amount * 0.25
                                ref2.invited_turnover = (ref2.invited_turnover or 0) + amount
                                ref2.total_bonus_earned = (ref2.total_bonus_earned or 0) + l2_bonus
                                comm2 = Commission(agent_id=inviter2.id, purchase_id=purchase.id, amount=l2_bonus, rate=rate, referral_level=2)
                                session.add(comm2)
                                trans2 = LoyaltyTransaction(agent_id=inviter2.id, transaction_type=TransactionType.REFERRAL_BONUS,
                                                           amount=l2_bonus, description=f"Реферальный бонус 2 уровня",
                                                           commission_id=comm2.id, purchase_id=purchase.id)
                                session.add(trans2)
                                inviter2.balance = (inviter2.balance or 0) + l2_bonus
                                inviter2.total_commission_earned = (inviter2.total_commission_earned or 0) + l2_bonus
        
        purchase.referral_bonus_level1 = l1_bonus
        purchase.referral_bonus_level2 = l2_bonus
        await session.flush()
        return purchase
    
    @staticmethod
    async def get_commissions_by_agent(session: AsyncSession, agent_id: int, skip: int = 0, limit: int = 50):
        total = (await session.execute(select(func.count(Commission.id)).where(Commission.agent_id == agent_id))).scalar() or 0
        result = await session.execute(select(Commission).where(Commission.agent_id == agent_id).order_by(Commission.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total
    
    @staticmethod
    async def get_transactions_by_agent(session: AsyncSession, agent_id: int, skip: int = 0, limit: int = 50):
        total = (await session.execute(select(func.count(LoyaltyTransaction.id)).where(LoyaltyTransaction.agent_id == agent_id))).scalar() or 0
        result = await session.execute(select(LoyaltyTransaction).where(LoyaltyTransaction.agent_id == agent_id).order_by(LoyaltyTransaction.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total
    
    @staticmethod
    async def withdraw_balance(session: AsyncSession, agent_id: int, amount: float) -> bool:
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if not agent: raise ValueError("Агент не найден")
        if agent.balance < amount: raise ValueError("Недостаточно средств")
        agent.balance -= amount
        session.add(LoyaltyTransaction(agent_id=agent.id, transaction_type=TransactionType.WITHDRAWAL, amount=-amount, description="Вывод средств"))
        await session.flush()
        return True
    
    @staticmethod
    async def adjust_balance(session: AsyncSession, agent_id: int, amount: float, description: str) -> bool:
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if not agent: raise ValueError("Агент не найден")
        agent.balance = (agent.balance or 0) + amount
        session.add(LoyaltyTransaction(agent_id=agent.id, transaction_type=TransactionType.CORRECTION, amount=amount, description=description))
        await session.flush()
        return True