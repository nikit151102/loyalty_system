"""Сервис отправки уведомлений через MAX API"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Отправка сообщений пользователям через MAX API"""
    
    @staticmethod
    async def send_message(user_id: int, text: str, attachments: list = None, notification_type: str = "unknown") -> bool:
        """
        Отправить сообщение пользователю через MAX Bot API.
        
        Args:
            user_id: MAX User ID получателя
            text: Текст сообщения
            attachments: Опциональные вложения (кнопки и т.п.)
            notification_type: Тип уведомления для логирования
        """
        logger.info(f"📨 Попытка отправки уведомления типа '{notification_type}' пользователю {user_id}")
        
        if not settings.MAX_BOT_TOKEN:
            logger.warning(f"⚠️ MAX_BOT_TOKEN не задан, уведомление для user_id={user_id} не отправлено")
            return False
        
        url = f"{settings.MAX_API_URL}/messages?user_id={user_id}"
        
        headers = {
            "Authorization": "f9LHodD0cOItvPIlwo5bsHYP41dZqM45Pnjuwt48tlZ7DNKnw-6_UeB6gaOqk63eIaLJhutpEGnGSe7YKPHz",
            "Content-Type": "application/json"
        }
        
        payload = {"text": text}
        if attachments:
            payload["attachments"] = attachments
        
        logger.debug(f"📤 Отправка запроса: user_id={user_id}, type={notification_type}")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Payload size: {len(str(payload))} bytes")
        logger.debug(f"   Has attachments: {bool(attachments)}")
        
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ Успешно отправлено уведомление '{notification_type}' "
                        f"пользователю {user_id} (HTTP {response.status_code})"
                    )
                    logger.debug(f"   Response: {response.text[:200]}")
                    return True
                
                elif response.status_code == 404:
                    logger.error(
                        f"❌ Ошибка 404 для user_id={user_id} (type={notification_type}): "
                        f"Пользователь не запускал бота или диалог не найден. "
                        f"Response: {response.text[:200]}"
                    )
                    return False
                
                elif response.status_code == 401:
                    logger.error(
                        f"❌ Ошибка 401 для user_id={user_id} (type={notification_type}): "
                        f"Неверный токен. Response: {response.text[:200]}"
                    )
                    return False
                
                else:
                    logger.error(
                        f"❌ Ошибка MAX API для user_id={user_id} (type={notification_type}): "
                        f"HTTP {response.status_code} - {response.text[:500]}"
                    )
                    logger.debug(f"   Full URL: {url}")
                    logger.debug(f"   Full payload: {payload}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error(
                f"⏱️ Timeout при отправке уведомления '{notification_type}' "
                f"пользователю {user_id} (>15 сек)"
            )
            return False
            
        except httpx.ConnectError as e:
            logger.error(
                f"🔌 Ошибка подключения к MAX API для user_id={user_id} "
                f"(type={notification_type}): {e}"
            )
            return False
            
        except Exception as e:
            logger.error(
                f"❌ Непредвиденная ошибка при отправке уведомления '{notification_type}' "
                f"пользователю {user_id}: {type(e).__name__}: {e}",
                exc_info=True
            )
            return False
    
    @staticmethod
    async def send_photo_message(user_id: int, photo_url: str, text: str = "", buttons: list = None) -> bool:
        """
        Отправить сообщение с фото (QR-код) через MAX API.
        
        Args:
            user_id: MAX User ID получателя
            photo_url: URL изображения
            text: Текст сообщения
            buttons: Опциональные inline-кнопки
        """
        logger.info(f"📷 Отправка фото пользователю {user_id}: {photo_url[:60]}...")
        
        url = f"https://platform-api2.max.ru/messages?user_id={user_id}"
        
        headers = {
            "Authorization": settings.MAX_BOT_TOKEN,
            "Content-Type": "application/json"
        }
        
        # Формируем вложения: фото + опционально кнопки
        attachments = [
            {
                "type": "photo",
                "payload": {
                    "url": photo_url
                }
            }
        ]
        
        if buttons:
            attachments.append({
                "type": "inline_keyboard",
                "payload": {
                    "buttons": buttons
                }
            })
        
        payload = {
            "text": text or " ",  # MAX требует текст
            "attachments": attachments
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"✅ Фото отправлено пользователю {user_id}")
                    return True
                else:
                    logger.error(
                        f"❌ Ошибка отправки фото: HTTP {response.status_code} - {response.text[:300]}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки фото: {e}")
            return False
            
    @staticmethod
    async def notify_application_approved(user_id: int, agent_id: int) -> bool:
        """Отправить уведомление об одобрении заявки"""
        logger.info(f"🎉 Отправка уведомления об одобрении: user_id={user_id}, agent_id={agent_id}")
        
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
        
        result = await NotificationService.send_message(
            user_id=user_id,
            text=text,
            attachments=attachments,
            notification_type="application_approved"
        )
        
        if result:
            logger.info(f"✅ Уведомление об одобрении отправлено: user_id={user_id} → agent_id={agent_id}")
        else:
            logger.error(f"❌ Не удалось отправить уведомление об одобрении: user_id={user_id}, agent_id={agent_id}")
        
        return result
    
    @staticmethod
    async def notify_application_rejected(user_id: int, reason: str) -> bool:
        """Отправить уведомление об отклонении заявки"""
        logger.info(f"❌ Отправка уведомления об отклонении: user_id={user_id}, reason={reason}")
        
        text = (
            f"❌ Ваша заявка отклонена\n\n"
            f"Причина: {reason or 'Не указана'}\n\n"
            "Вы можете подать новую заявку через /start"
        )
        
        result = await NotificationService.send_message(
            user_id=user_id,
            text=text,
            notification_type="application_rejected"
        )
        
        if result:
            logger.info(f"✅ Уведомление об отклонении отправлено: user_id={user_id}")
        else:
            logger.error(f"❌ Не удалось отправить уведомление об отклонении: user_id={user_id}")
        
        return result
    
    @staticmethod
    async def notify_new_purchase(user_id: int, client_name: str, amount: float, commission: float) -> bool:
        """Уведомление агенту о новой покупке его клиента"""
        logger.info(
            f"💰 Отправка уведомления о покупке: user_id={user_id}, "
            f"client={client_name}, amount={amount:.2f}₽, commission={commission:.2f}₽"
        )
        
        text = (
            f"💰 Новая покупка!\n\n"
            f"👤 Клиент: {client_name}\n"
            f"🛍 Сумма: {amount:.2f} ₽\n"
            f"💵 Ваша комиссия: {commission:.2f} ₽\n\n"
            "Баланс обновлён. Проверьте статистику."
        )
        
        result = await NotificationService.send_message(
            user_id=user_id,
            text=text,
            notification_type="new_purchase"
        )
        
        if result:
            logger.info(
                f"✅ Уведомление о покупке отправлено: user_id={user_id}, "
                f"client={client_name}, commission={commission:.2f}₽"
            )
        else:
            logger.error(
                f"❌ Не удалось отправить уведомление о покупке: user_id={user_id}, "
                f"client={client_name}"
            )
        
        return result
    
    @staticmethod
    async def notify_admins(text: str, notification_type: str = "admin_notification") -> bool:
        """Отправить уведомление всем администраторам"""
        if not settings.ADMIN_USER_IDS:
            logger.warning("⚠️ ADMIN_USER_IDS не задан, уведомления админам не отправлены")
            return False
        
        admin_ids = settings.admin_ids
        logger.info(f"📨 Отправка уведомления {len(admin_ids)} администраторам: {admin_ids}")
        
        success = True
        for admin_id in admin_ids:
            logger.info(f"   → Отправка админу {admin_id}")
            result = await NotificationService.send_message(
                user_id=admin_id,
                text=text,
                notification_type=f"{notification_type}_admin_{admin_id}"
            )
            if not result:
                logger.error(f"   ❌ Не удалось отправить админу {admin_id}")
                success = False
            else:
                logger.info(f"   ✅ Успешно отправлено админу {admin_id}")
        
        return success