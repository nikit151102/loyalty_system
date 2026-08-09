"""Регистрация агента"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState, REGISTRATION_TYPES
from utils import normalize_phone, validate_email
from api_client import api_client

def register_registration_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "become_agent")
    async def become_agent(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        user_states[user_id] = UserState.REG_WAITING_PHONE
        user_data[user_id] = {"registration": {}}
        await bot.send_message(chat_id=chat_id, text="📱 **Шаг 1/3 - Номер телефона**\n\nВведите номер телефона:\nПример: +79991234567")
    
    @dp.message_callback(F.callback.payload == "cancel_registration")
    async def cancel_reg(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        user_states[user_id] = UserState.IDLE
        user_data[user_id] = {}
        from handlers.start import send_start_menu
        await send_start_menu(bot, chat_id, "друг")
    
    @dp.message_callback(F.callback.payload.startswith("reg_type_"))
    async def select_type(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        reg_type = event.callback.payload.replace("reg_type_", "")
        data = user_data.get(user_id, {})
        reg_data = data.get("registration", {})
        reg_data["type"] = reg_type
        type_name = REGISTRATION_TYPES.get(reg_type, reg_type)
        
        buttons = [
            [CallbackButton(text="✅ Отправить заявку", payload="submit_registration", intent=Intent.POSITIVE)],
            [CallbackButton(text="✏️ Изменить данные", payload="become_agent", intent=Intent.DEFAULT)],
            [CallbackButton(text="❌ Отменить", payload="cancel_registration", intent=Intent.NEGATIVE)],
        ]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=f"📋 **Подтверждение**\n\n📱 {reg_data.get('phone')}\n📧 {reg_data.get('email')}\n🏷️ {type_name}\n\nВсё верно?", attachments=[attachment])
        user_states[user_id] = UserState.REG_CONFIRMATION
    
    @dp.message_callback(F.callback.payload == "submit_registration")
    async def submit(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        data = user_data.get(user_id, {})
        reg_data = data.get("registration", {})
        
        if not all(k in reg_data for k in ["phone", "email", "type"]):
            await bot.send_message(chat_id=chat_id, text="❌ Не все данные заполнены.")
            return
        
        result = await api_client.register_agent(user_id, reg_data["phone"], reg_data["email"], reg_data["type"], data.get("referral_code"))
        if result and not result.get("error"):
            user_states[user_id] = UserState.IDLE
            user_data[user_id] = {}
            await bot.send_message(chat_id=chat_id, text="✅ **Заявка отправлена!**\n\n⏳ Ожидайте рассмотрения администратором.")
        else:
            err = result.get("error", "Неизвестная ошибка") if result else "Ошибка"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")
    
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        chat_id = event.message.recipient.chat_id
        if text.startswith("/"): return
        
        state = user_states.get(user_id)
        data = user_data.get(user_id, {})
        reg_data = data.get("registration", {})
        
        if state == UserState.REG_WAITING_PHONE:
            phone = normalize_phone(text)
            if not phone:
                await event.message.answer("❌ Неверный формат телефона")
                return
            reg_data["phone"] = phone
            user_states[user_id] = UserState.REG_WAITING_EMAIL
            await event.message.answer(f"✅ Телефон сохранён: {phone}\n\n📧 **Шаг 2/3 - Email**\n\nВведите email:")
            return
        
        if state == UserState.REG_WAITING_EMAIL:
            if not validate_email(text):
                await event.message.answer("❌ Неверный формат email")
                return
            reg_data["email"] = text
            user_states[user_id] = UserState.REG_WAITING_TYPE
            buttons = [
                [CallbackButton(text="👤 Самозанятый", payload="reg_type_self_employed", intent=Intent.DEFAULT)],
                [CallbackButton(text="📋 ИП", payload="reg_type_ip", intent=Intent.DEFAULT)],
                [CallbackButton(text="🏢 Юр. лицо", payload="reg_type_legal_entity", intent=Intent.DEFAULT)],
                [CallbackButton(text="❌ Отмена", payload="cancel_registration", intent=Intent.NEGATIVE)],
            ]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await event.message.answer(f"✅ Email сохранён: {text}\n\n🏷️ **Шаг 3/3 - Тип регистрации**", attachments=[attachment])
            return