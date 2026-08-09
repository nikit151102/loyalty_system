"""Клиенты"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState, CLIENT_TYPES
from utils import normalize_phone, validate_email, validate_inn, format_money
from api_client import api_client

def register_clients_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "my_clients")
    async def my_clients(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        clients = await api_client.get_my_clients(token, skip=0, limit=20)
        if not clients:
            text = "👥 **Мои клиенты**\n\nУ вас пока нет клиентов."
            buttons = [
                [CallbackButton(text="➕ Добавить клиента", payload="add_client", intent=Intent.POSITIVE)],
                [CallbackButton(text="🏠 Назад", payload="agent_menu", intent=Intent.DEFAULT)],
            ]
        else:
            text = "👥 **Мои клиенты**\n\n"
            for i, c in enumerate(clients, 1):
                text += f"**{i}. {c['full_name']}**\n   📱 {c['phone']}\n   💰 {format_money(c.get('total_purchases_amount', 0))}\n   🛍 {c.get('purchases_count', 0)} покупок\n\n"
            buttons = [
                [CallbackButton(text="➕ Добавить клиента", payload="add_client", intent=Intent.POSITIVE)],
                [CallbackButton(text="🏠 Назад", payload="agent_menu", intent=Intent.DEFAULT)],
            ]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
    
    @dp.message_callback(F.callback.payload == "add_client")
    async def add_client_start(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        user_states[user_id] = UserState.ADD_CLIENT_NAME
        user_data[user_id] = {"new_client": {}}
        await bot.send_message(chat_id=chat_id, text="➕ **Добавление клиента**\n\n**Шаг 1/5 - ФИО**\n\nВведите полное имя клиента:")
    
    @dp.message_callback(F.callback.payload == "cancel_add_client")
    async def cancel_add(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        user_states[user_id] = UserState.IDLE
        await bot.send_message(chat_id=event.message.recipient.chat_id, text="❌ Отменено")
    
    @dp.message_callback(F.callback.payload.startswith("client_type_"))
    async def select_client_type(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        client_type = event.callback.payload.replace("client_type_", "")
        data = user_data.get(user_id, {})
        client_data = data.get("new_client", {})
        client_data["type"] = client_type
        type_name = CLIENT_TYPES.get(client_type, client_type)
        
        buttons = [
            [CallbackButton(text="✅ Подтвердить", payload="confirm_add_client", intent=Intent.POSITIVE)],
            [CallbackButton(text="❌ Отмена", payload="cancel_add_client", intent=Intent.NEGATIVE)],
        ]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        text = (
            f"📋 **Подтверждение**\n\n"
            f"👤 ФИО: {client_data.get('full_name')}\n"
            f"📱 Телефон: {client_data.get('phone')}\n"
            f"📧 Email: {client_data.get('email') or '—'}\n"
            f"🆔 ИНН: {client_data.get('inn') or '—'}\n"
            f"🏷️ Тип: {type_name}"
        )
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
    
    @dp.message_callback(F.callback.payload == "confirm_add_client")
    async def confirm(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        data = user_data.get(user_id, {})
        client_data = data.get("new_client", {})
        profile = await api_client.get_my_profile(token)
        if not profile or profile.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка")
            return
        
        payload = {
            "agent_id": profile.get("id"),
            "full_name": client_data.get("full_name"),
            "phone": client_data.get("phone"),
            "email": client_data.get("email"),
            "inn": client_data.get("inn"),
            "client_type": client_data.get("type", "individual"),
        }
        result = await api_client.add_client(token, payload)
        if result and not result.get("error"):
            user_states[user_id] = UserState.IDLE
            user_data[user_id] = {}
            text = (
                "✅ **Клиент добавлен!**\n\n"
                f"👤 {result.get('full_name')}\n"
                f"📱 {result.get('phone')}\n"
                f"🔑 Код: `{result.get('referral_code')}`\n\n"
                f"💰 Комиссия: 3-5% (от оборота)"
            )
            buttons = [
                [CallbackButton(text="👥 К списку", payload="my_clients", intent=Intent.DEFAULT)],
                [CallbackButton(text="🏠 В меню", payload="agent_menu", intent=Intent.DEFAULT)],
            ]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
        else:
            err = result.get("error", "Неизвестная ошибка") if result else "Ошибка"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")
    
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        chat_id = event.message.recipient.chat_id
        if text.startswith("/"): return
        
        state = user_states.get(user_id)
        data = user_data.get(user_id, {})
        client_data = data.get("new_client", {})
        
        if state == UserState.ADD_CLIENT_NAME:
            if len(text) < 2:
                await event.message.answer("❌ Имя слишком короткое")
                return
            client_data["full_name"] = text
            user_states[user_id] = UserState.ADD_CLIENT_PHONE
            await event.message.answer(f"✅ Имя сохранено: {text}\n\n**Шаг 2/5 - Телефон**\n\nВведите номер телефона:")
            return
        
        if state == UserState.ADD_CLIENT_PHONE:
            phone = normalize_phone(text)
            if not phone:
                await event.message.answer("❌ Неверный формат телефона")
                return
            existing = await api_client.get_client_by_phone(phone)
            if existing and not existing.get("error"):
                await event.message.answer(f"❌ Клиент с телефоном {phone} уже существует")
                return
            client_data["phone"] = phone
            user_states[user_id] = UserState.ADD_CLIENT_EMAIL
            await event.message.answer(f"✅ Телефон сохранён: {phone}\n\n**Шаг 3/5 - Email** (необязательно)\n\nВведите email или '-' чтобы пропустить:")
            return
        
        if state == UserState.ADD_CLIENT_EMAIL:
            if text == "-":
                client_data["email"] = None
            elif validate_email(text):
                client_data["email"] = text
            else:
                await event.message.answer("❌ Неверный email")
                return
            user_states[user_id] = UserState.ADD_CLIENT_INN
            await event.message.answer("**Шаг 4/5 - ИНН** (необязательно)\n\nВведите ИНН или '-':")
            return
        
        if state == UserState.ADD_CLIENT_INN:
            if text == "-":
                client_data["inn"] = None
            elif validate_inn(text):
                client_data["inn"] = text
            else:
                await event.message.answer("❌ Неверный ИНН (10 или 12 цифр)")
                return
            user_states[user_id] = UserState.ADD_CLIENT_TYPE
            buttons = [
                [CallbackButton(text="👤 Физ. лицо", payload="client_type_individual", intent=Intent.DEFAULT)],
                [CallbackButton(text="🏢 Юр. лицо", payload="client_type_legal_entity", intent=Intent.DEFAULT)],
            ]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await event.message.answer("**Шаг 5/5 - Тип клиента**", attachments=[attachment])
            return