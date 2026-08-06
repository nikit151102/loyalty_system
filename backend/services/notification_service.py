"""Сервис отправки уведомлений через MAX API"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Отправка сообщений пользователям через MAX API"""
    
    @staticmethod
    async def send_message(user_id: int, text: str, attachments: list = None) -> bool:
        """
        Отправить сообщение пользователю через MAX Bot API.
        
        Правильный формат MAX API:
        - URL: https://platform-api2.max.ru/messages?user_id=XXX
        - Authorization: <token> (БЕЗ Bearer!)
        - Body: {"text": "...", "attachments": [...]}
        """
        if not settings.MAX_BOT_TOKEN:
            logger.warning("MAX_BOT_TOKEN не задан, уведомление не отправлено")
            return False
        
        url = f"{settings.MAX_API_URL}/messages?user_id={user_id}"
        
        headers = {
            "Authorization": settings.MAX_BOT_TOKEN,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text
        }
        
        if attachments:
            payload["attachments"] = attachments
        
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
                    return True
                else:
                    logger.error(
                        f"❌ Ошибка MAX API: {response.status_code} - {response.text[:500]}"
                    )
                    logger.debug(f"URL: {url[:80]}...")
                    logger.debug(f"Payload: {payload}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
            return False
    
    @staticmethod
    async def notify_application_approved(user_id: int, agent_id: int) -> bool:
        """Отправить уведомление об одобрении заявки"""
        text = (
            "🎉 Поздравляем! Ваша заявка одобрена!\n\n"
            "✅ Теперь вы являетесь агентом программы лояльности.\n\n"
            "🚀 Что доступно:\n"
            "• 👥 Добавлять клиентов\n"
            "• 💰 Получать комиссию 3-5% с покупок\n"
            "• 🔗 Приглашать других агентов за бонусами\n"
            "• 📊 Отслеживать статистику\n\n"
            "Нажмите /start чтобы открыть главное меню агента."
        )
        
        attachments = [
            {
                "type": "inline_keyboard",
                "payload": {
                    "buttons": [
                        [
                            {
                                "type": "callback",
                                "text": "🏠 Открыть меню агента",
                                "payload": "agent_menu"
                            }
                        ]
                    ]
                }
            }
        ]
        
        return await NotificationService.send_message(
            user_id=user_id,
            text=text,
            attachments=attachments
        )
    
    @staticmethod
    async def notify_application_rejected(user_id: int, reason: str) -> bool:
        """Отправить уведомление об отклонении заявки"""
        text = (
            f"❌ Ваша заявка отклонена\n\n"
            f"Причина: {reason or 'Не указана'}\n\n"
            "Вы можете подать новую заявку через /start"
        )
        return await NotificationService.send_message(user_id=user_id, text=text)
    
    @staticmethod
    async def notify_new_purchase(user_id: int, client_name: str, amount: float, commission: float) -> bool:
        """Уведомление агенту о новой покупке его клиента"""
        text = (
            f"💰 Новая покупка!\n\n"
            f"👤 Клиент: {client_name}\n"
            f"🛍 Сумма: {amount:.2f} ₽\n"
            f"💵 Ваша комиссия: {commission:.2f} ₽\n\n"
            "Баланс обновлён. Проверьте статистику."
        )
        return await NotificationService.send_message(user_id=user_id, text=text)
    
    @staticmethod
    async def notify_admins(text: str) -> bool:
        """Отправить уведомление всем администраторам"""
        if not settings.ADMIN_USER_IDS:
            return False
        
        success = True
        for admin_id in settings.admin_ids:
            result = await NotificationService.send_message(user_id=admin_id, text=text)
            if not result:
                success = False
        return success