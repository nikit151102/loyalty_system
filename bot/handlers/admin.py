"""Админ"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from config import config
from api_client import api_client

def register_admin_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload.startswith("approve_app_"))
    async def approve(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        if user_id not in config.admin_ids:
            await bot.send_message(chat_id=chat_id, text="❌ Доступ запрещён")
            return
        app_id = int(event.callback.payload.replace("approve_app_", ""))
        result = await api_client.approve_application(app_id, user_id)
        if result and not result.get("error"):
            await bot.send_message(chat_id=chat_id, text=f"✅ Заявка #{app_id} одобрена!")
        else:
            err = result.get("error", "Ошибка") if result else "Ошибка"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")
    
    @dp.message_callback(F.callback.payload.startswith("reject_app_"))
    async def reject(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        if user_id not in config.admin_ids:
            await bot.send_message(chat_id=chat_id, text="❌ Доступ запрещён")
            return
        app_id = int(event.callback.payload.replace("reject_app_", ""))
        result = await api_client.reject_application(app_id, user_id, "Заявка отклонена")
        if result and not result.get("error"):
            await bot.send_message(chat_id=chat_id, text=f"❌ Заявка #{app_id} отклонена.")
        else:
            err = result.get("error", "Ошибка") if result else "Ошибка"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")