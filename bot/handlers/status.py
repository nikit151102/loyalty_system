"""Проверка статуса"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from api_client import api_client

def register_status_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "check_status")
    async def check_status(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        token = await api_client.login(user_id)
        if token:
            buttons = [[CallbackButton(text="🏠 В главное меню", payload="agent_menu", intent=Intent.DEFAULT)]]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await bot.send_message(chat_id=chat_id, text="✅ **Вы уже являетесь агентом!**", attachments=[attachment])
            return
        
        app = await api_client.get_application_status(user_id)
        if not app or app.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ У вас нет активных заявок.")
            return
        
        status = app.get("status", "unknown")
        if status == "pending":
            text = "⏳ **Статус: На рассмотрении**\n\nМы уведомим вас после одобрения."
        elif status == "approved":
            text = "✅ **Статус: Одобрена!**"
        elif status == "rejected":
            reason = app.get("rejection_reason", "Не указана")
            text = f"❌ **Статус: Отклонена**\n\nПричина: {reason}"
        else:
            text = f"❓ Статус: {status}"
        
        buttons = [[CallbackButton(text="🏠 В главное меню", payload="back_to_start", intent=Intent.DEFAULT)]]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
    
    @dp.message_callback(F.callback.payload == "back_to_start")
    async def back(event: MessageCallback):
        await event.answer()
        from handlers.start import send_start_menu
        await send_start_menu(bot, event.message.recipient.chat_id, "друг")