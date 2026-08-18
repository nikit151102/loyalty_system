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
        full_name: str,
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
        
        # Нормализуем город для проверки (с проверкой на None)
        normalized_city = city.strip().lower() if city else ""
        
        # Очищаем номер телефона от префиксов
        clean_phone = phone.replace('+7', '').replace('8', '').replace(' ', '').replace('-', '')
        
        # Генерируем реферальный код на основе города
        if 'барнаул' in normalized_city:
            generated_referral_code = f"V{clean_phone}"
        else:
            generated_referral_code = f"G{clean_phone}"
        
        application = Application(
            full_name=full_name, 
            max_user_id=max_user_id,
            phone=phone,
            email=email,
            city=city,
            registration_type=registration_type,
            status=ApplicationStatus.PENDING,
        )
        
        # Сохраняем сгенерированный код в rejection_reason с префиксом REF:
        application.rejection_reason = f"REF:{generated_referral_code}"
        
        session.add(application)
        await session.flush()
        
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
    async def approve_application(
        session: AsyncSession, 
        application_id: int, 
        reviewed_by: int
    ) -> Agent:
        """Одобрить заявку и создать агента"""
        from datetime import datetime
        from models.db_models import ApplicationStatus, Application
        
        # Получаем заявку
        app = await session.get(Application, application_id)
        if not app:
            raise ValueError("Заявка не найдена")
        
        if app.status != ApplicationStatus.PENDING:
            raise ValueError(f"Заявка уже обработана. Статус: {app.status}")
        
        # Создаем или получаем агента (теперь с проверкой на дубликаты)
        agent = await AgentService.create_agent(
            session=session,
            full_name=app.full_name,
            max_user_id=app.max_user_id,
            phone=app.phone,
            email=app.email,
            city=app.city,
            registration_type=app.registration_type.value,
            referral_code=app.referral_code if hasattr(app, 'referral_code') else None
        )
        
        # Обновляем заявку
        app.status = ApplicationStatus.APPROVED
        app.agent_id = agent.id
        app.reviewed_by = reviewed_by
        app.reviewed_at = datetime.utcnow()
        
        await session.flush()
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