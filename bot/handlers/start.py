"""Стартовый хендлер"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, BotStarted, Command, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState

def register_start_handlers(dp: Dispatcher, bot, user_states, user_data, api_client):
    
    @dp.bot_started()
    async def handle_bot_started(event: BotStarted):
        user = event.user
        user_id = user.user_id
        chat_id = event.chat_id
        name = getattr(user, "first_name", None) or "друг"
        user_states[user_id] = UserState.IDLE
        user_data[user_id] = {}
        
        token = await api_client.login(user_id)
        if token:
            await send_agent_menu(bot, chat_id, user_id, name, api_client, token)
            return
        
        app_status = await api_client.get_application_status(user_id)
        if app_status and not app_status.get("error"):
            status = app_status.get("status")
            if status == "pending":
                await bot.send_message(chat_id=chat_id, text=f"👋 {name}!\n\n⏳ Ваша заявка на рассмотрении.")
                return
            elif status == "rejected":
                reason = app_status.get("rejection_reason", "Не указана")
                await bot.send_message(chat_id=chat_id, text=f"👋 {name}!\n\n❌ Заявка отклонена. Причина: {reason}")
        
        await send_start_menu(bot, chat_id, name)
    
    @dp.message_created(Command("start"))
    async def cmd_start(event: MessageCreated):
        user = event.message.sender
        user_id = user.user_id
        chat_id = event.message.recipient.chat_id
        name = getattr(user, "first_name", None) or "друг"
        user_states[user_id] = UserState.IDLE
        user_data[user_id] = {}
        
        token = await api_client.login(user_id)
        if token:
            await send_agent_menu(bot, chat_id, user_id, name, api_client, token)
            return
        
        app_status = await api_client.get_application_status(user_id)
        if app_status and not app_status.get("error"):
            status = app_status.get("status")
            if status == "pending":
                await bot.send_message(chat_id=chat_id, text=f"👋 {name}!\n\n⏳ Ваша заявка на рассмотрении.")
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