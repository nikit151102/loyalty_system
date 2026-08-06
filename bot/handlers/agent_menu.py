"""Меню агента"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from api_client import api_client

def register_agent_menu_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "agent_menu")
    async def agent_menu(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        profile = await api_client.get_my_profile(token)
        if not profile or profile.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка")
            return
        from handlers.start import send_agent_menu
        name = getattr(event.callback.user, "first_name", None) or "агент"
        await send_agent_menu(bot, chat_id, user_id, name, api_client, token)
    
    @dp.message_callback(F.callback.payload == "my_profile")
    async def my_profile(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        profile = await api_client.get_my_profile(token)
        if not profile or profile.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка")
            return
        text = (
            f"💼 **Мой профиль**\n\n"
            f"🆔 ID: {profile.get('id')}\n"
            f"📱 Телефон: {profile.get('phone')}\n"
            f"📧 Email: {profile.get('email')}\n"
            f"🏷️ Тип: {profile.get('registration_type')}\n"
            f"📊 Статус: {profile.get('status')}\n\n"
            f"💰 Баланс: {profile.get('balance', 0):.2f} ₽\n"
            f"👥 Клиентов: {profile.get('total_clients', 0)}\n"
            f"🛍 Оборот: {profile.get('total_purchases_amount', 0):.2f} ₽\n"
            f"💵 Заработано: {profile.get('total_commission_earned', 0):.2f} ₽\n"
            f"🔗 Рефералов: {profile.get('total_referrals_count', 0)}\n\n"
            f"🔑 Реферальный код: `{profile.get('referral_code')}`"
        )
        buttons = [[CallbackButton(text="🏠 Назад", payload="agent_menu", intent=Intent.DEFAULT)]]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])