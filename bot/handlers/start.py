"""Стартовый хендлер с поддержкой рефералок"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, BotStarted, Command, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState
import logging

logger = logging.getLogger(__name__)


def register_start_handlers(dp: Dispatcher, bot, user_states, user_data, api_client):
    

    @dp.bot_started()
    async def handle_bot_started(event: BotStarted):
        user = event.user
        user_id = user.user_id
        chat_id = event.chat_id
        name = getattr(user, "first_name", None) or "друг"
        
        user_states[user_id] = UserState.IDLE
        user_data[user_id] = {}
        
        # ===== ПЕРЕХВАТ РЕФЕРАЛЬНОГО КОДА =====
        referral_code = None
        if hasattr(event, 'payload') and event.payload:
            referral_code = event.payload
            logger.info(f"🔗 РЕФЕРАЛКА: user_id={user_id}, code='{referral_code}'")
        
        if referral_code:
            # Ищем агента по коду
            agent_info = await api_client.get_agent_by_referral(referral_code)
            
            if agent_info and not agent_info.get("error"):
                # Сохраняем информацию
                user_data[user_id] = {
                    "referral_code": referral_code,
                    "referrer_agent_info": agent_info
                }
                
                logger.info(f"✅ Агент найден: id={agent_info.get('id')}")
                
                # Показываем меню клиента по рефералке
                await send_client_referral_menu(bot, chat_id, name, referral_code, agent_info)
                return
            else:
                logger.warning(f"⚠️ Агент с кодом '{referral_code}' не найден")
        
        # ===== Обычная логика =====
        token = await api_client.login(user_id)
        if token:
            await send_agent_menu(bot, chat_id, user_id, name, api_client, token)
            return
        
        await send_start_menu(bot, chat_id, name)


        async def send_client_referral_menu(bot, chat_id: int, name: str, referral_code: str, agent_info: dict):
            """Меню для клиента, пришедшего по рефералке"""
            text = (
                f"👋 Здравствуйте, {name}!\n\n"
                f"🎁 Вы пришли по приглашению агента\n"
                f"🔑 Код приглашения: `{referral_code}`\n\n"
                f"**Что можно сделать:**\n"
                f"• 🛍 Зарегистрироваться как клиент и получать кэшбэк\n"
                f"• 🚀 Сразу стать агентом и зарабатывать\n\n"
                f"Выберите действие:"
            )
            
            buttons = [
                [CallbackButton(text="🛍 Зарегистрироваться как клиент", payload="become_client", intent=Intent.POSITIVE)],
                [CallbackButton(text="🚀 Стать агентом сразу", payload="become_agent", intent=Intent.DEFAULT)],
                [CallbackButton(text="❓ Что такое программа?", payload="help", intent=Intent.DEFAULT)],
            ]
            
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
            
        @dp.message_created(Command("start"))
        async def cmd_start(event: MessageCreated):
            user = event.message.sender
            user_id = user.user_id
            chat_id = event.message.recipient.chat_id
            name = getattr(user, "first_name", None) or "друг"
            
            user_states[user_id] = UserState.IDLE
            user_data[user_id] = {}
            
            # ===== 🎯 ПЕРЕХВАТ РЕФЕРАЛЬНОГО КОДА из /start XXX =====
            # В MAX команда может приходить как /start REF_CODE
            text = event.message.body.text.strip()
            referral_code = None
            
            # Извлекаем аргумент после /start
            if text.startswith("/start ") or text.startswith("/start@"):
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    referral_code = parts[1].strip()
                    logger.info(f"🔗 РЕФЕРАЛКА через /start! user_id={user_id}, code='{referral_code}'")
                    user_data[user_id] = {"referral_code": referral_code}
            
            if referral_code:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"👋 {name}!\n\n"
                        f"Вы пришли по приглашению (код: `{referral_code}`)."
                )
            else:
                logger.info(f"👤 Обычный /start от user_id={user_id}")
            
            # ===== Обычная логика =====
            token = await api_client.login(user_id)
            if token:
                await send_agent_menu(bot, chat_id, user_id, name, api_client, token)
                return
            
            await send_start_menu(bot, chat_id, name)


async def send_start_menu(bot, chat_id, name):
    text = (
        f"👋 Здравствуйте, {name}!\n\n"
        "Я бот программы лояльности.\n\n"
        "🎯 **Возможности:**\n"
        "• Стать агентом нашей программы\n"
        "• Зарабатывать комиссию с продаж\n"
        "• Приглашать других агентов\n\n"
        "💰 **Комиссии:**\n"
        "• 3% до 100 000 ₽ оборота\n"
        "• 5% свыше 100 000 ₽ оборота"
    )
    buttons = [
        [CallbackButton(text="🚀 Стать агентом", payload="become_agent", intent=Intent.POSITIVE)],
        [CallbackButton(text="📋 Проверить статус", payload="check_status", intent=Intent.DEFAULT)],
        [CallbackButton(text="❓ Помощь", payload="help", intent=Intent.DEFAULT)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])


async def send_agent_menu(bot, chat_id, user_id, name, api_client, token):
    profile = await api_client.get_my_profile(token)
    if not profile or profile.get("error"):
        await bot.send_message(chat_id=chat_id, text=f"👋 {name}!\n\nНе удалось получить профиль.")
        return
    
    text = (
        f"👋 Здравствуйте, {name}!\n\n"
        "✅ **Вы являетесь агентом программы**\n\n"
        f"💰 **Баланс:** {profile.get('balance', 0):.2f} ₽\n"
        f"👥 **Клиентов:** {profile.get('total_clients', 0)}"
    )
    buttons = [
        [CallbackButton(text="👥 Мои клиенты", payload="my_clients", intent=Intent.DEFAULT)],
        [CallbackButton(text="➕ Добавить клиента", payload="add_client", intent=Intent.POSITIVE)],
        [CallbackButton(text="📊 Статистика", payload="statistics", intent=Intent.DEFAULT)],
        [CallbackButton(text="🔗 Реферальная ссылка", payload="referral", intent=Intent.DEFAULT)],
        [CallbackButton(text="💼 Мой профиль", payload="my_profile", intent=Intent.DEFAULT)],
        [CallbackButton(text="❓ Помощь", payload="help", intent=Intent.DEFAULT)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])