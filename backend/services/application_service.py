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
    async def create_application(
        session: AsyncSession, 
        max_user_id: int, 
        phone: str, 
        email: str, 
        city: str,
        registration_type: RegistrationType, 
        referral_code: Optional[str] = None
    ) -> Application:
        existing = await ApplicationService.get_pending_by_user(session, max_user_id)
        if existing: 
            raise ValueError("Заявка уже на рассмотрении")
        
        # Нормализуем город для проверки
        normalized_city = city.strip().lower()
        
        # Очищаем номер телефона от префиксов
        clean_phone = phone.replace('+7', '').replace('8', '').replace(' ', '').replace('-', '')
        
        # Генерируем реферальный код на основе города
        if 'барнаул' in normalized_city:  # Проверяем наличие слова "барнаул" (даже с опечатками)
            generated_referral_code = f"V{clean_phone}"
        else:
            generated_referral_code = f"G{clean_phone}"
        
        application = Application(
            max_user_id=max_user_id,
            phone=phone,
            email=email,
            city=city,  # Сохраняем город
            referral_code=generated_referral_code,  # Сохраняем сгенерированный код
            registration_type=registration_type,
            status=ApplicationStatus.PENDING,
        )
        
        session.add(application)
        await session.flush()
        
        # Если был передан внешний referral_code (от приглашающего агента), сохраняем его отдельно
        if referral_code:
            # Можно добавить поле invited_by_referral_code в модель Application
            # или использовать для поиска пригласившего агента
            pass
        
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
        import asyncio
        from services.notification_service import NotificationService
        
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()
        if not application: raise ValueError("Заявка не найдена")
        # if application.status != ApplicationStatus.PENDING: raise ValueError("Заявка уже рассмотрена")
        
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
            # Реферальная связь 2 уровня
            if inviter and inviter.invited_by_agent_id:
                await ReferralService.create_referral(session, inviter.invited_by_agent_id, agent.id, 2)
        
        # Сохраняем user_id для отправки уведомления ПОСЛЕ коммита
        user_id_to_notify = application.max_user_id
        agent_id_for_notify = agent.id
        
        await session.flush()
        
        # ===== НОВОЕ: Отправка уведомления (асинхронно, не блокируя транзакцию) =====
        try:
            # Создаём задачу, которая выполнится параллельно
            asyncio.create_task(
                NotificationService.notify_application_approved(
                    user_id=user_id_to_notify,
                    agent_id=agent_id_for_notify
                )
            )
        except Exception as e:
            # Не даём ошибке уведомления сломать одобрение заявки
            import logging
            logging.getLogger(__name__).error(f"Ошибка уведомления: {e}")
        
        return agent


    @staticmethod
    async def reject_application(session: AsyncSession, application_id: int, reviewed_by: int, rejection_reason: str = None):
        import asyncio
        from services.notification_service import NotificationService
        
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()
        if not application: raise ValueError("Заявка не найдена")
        if application.status != ApplicationStatus.PENDING: raise ValueError("Заявка уже рассмотрена")
        
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = rejection_reason
        application.reviewed_by = reviewed_by
        application.reviewed_at = datetime.utcnow()
        
        # Сохраняем для уведомления
        user_id_to_notify = application.max_user_id
        reason_for_notify = rejection_reason
        
        await session.flush()
        
        # ===== НОВОЕ: Уведомление об отклонении =====
        try:
            asyncio.create_task(
                NotificationService.notify_application_rejected(
                    user_id=user_id_to_notify,
                    reason=reason_for_notify
                )
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Ошибка уведомления: {e}")
        
        return application