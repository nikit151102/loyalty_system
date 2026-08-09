"""Единый роутер текстовых сообщений - обрабатывает ВСЕ состояния"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState
from utils import normalize_phone, validate_email, validate_inn, format_phone
from api_client import api_client
import logging

logger = logging.getLogger(__name__)


def register_text_router(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_created(F.message.body.text)
    async def handle_all_text(event: MessageCreated):
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        chat_id = event.message.recipient.chat_id
        
        if text.startswith("/"):
            return
        
        state = user_states.get(user_id, UserState.IDLE)
        data = user_data.get(user_id, {})
        
        logger.info(f"📥 user_id={user_id}, state={state.value}")
        
        # Передаём user_states в обработчики
        if state == UserState.REG_WAITING_PHONE:
            phone = normalize_phone(text)
            if not phone:
                await event.message.answer("❌ Неверный формат телефона")
                return
            data.setdefault("registration", {})["phone"] = phone
            user_states[user_id] = UserState.REG_WAITING_EMAIL  # ← переключаем
            await event.message.answer(
                f"✅ Телефон сохранён: {phone}\n\n"
                "📧 **Шаг 2/3 - Email**\n\nВведите ваш email:"
            )
            return
        
        if state == UserState.REG_WAITING_EMAIL:
            if not validate_email(text):
                await event.message.answer("❌ Неверный формат email")
                return
            data.setdefault("registration", {})["email"] = text
            user_states[user_id] = UserState.REG_WAITING_TYPE
            buttons = [
                [CallbackButton(text="👤 Самозанятый", payload="reg_type_self_employed", intent=Intent.DEFAULT)],
                [CallbackButton(text="📋 ИП", payload="reg_type_ip", intent=Intent.DEFAULT)],
                [CallbackButton(text="🏢 Юр. лицо", payload="reg_type_legal_entity", intent=Intent.DEFAULT)],
            ]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            await event.message.answer("🏷️ **Шаг 3/3 - Тип регистрации**", attachments=[attachment])
            return
        
        # РЕГИСТРАЦИЯ КЛИЕНТА
        if state == UserState.CLIENT_REG_WAITING_NAME:
            if len(text) < 2:
                await event.message.answer("❌ Имя слишком короткое")
                return
            data.setdefault("new_client_data", {})["full_name"] = text
            user_states[user_id] = UserState.CLIENT_REG_WAITING_PHONE  # ← переключаем
            logger.info(f"✅ ФИО сохранено: {text}")
            await event.message.answer(
                f"✅ ФИО сохранено: {text}\n\n"
                "**Шаг 2/4 - Телефон**\n\nВведите ваш номер телефона:"
            )
            return
        
        if state == UserState.CLIENT_REG_WAITING_PHONE:
            phone = normalize_phone(text)
            if not phone:
                await event.message.answer("❌ Неверный формат телефона")
                return
            existing = await api_client.get_client_by_phone(phone)
            if existing and not existing.get("error"):
                await event.message.answer(f"❌ Клиент с телефоном {phone} уже существует")
                return
            data.setdefault("new_client_data", {})["phone"] = phone
            user_states[user_id] = UserState.CLIENT_REG_WAITING_EMAIL
            await event.message.answer(
                f"✅ Телефон сохранён: {format_phone(phone)}\n\n"
                "**Шаг 3/4 - Email**\n\nВведите ваш email:"
            )
            return
        
        if state == UserState.CLIENT_REG_WAITING_EMAIL:
            if not validate_email(text):
                await event.message.answer("❌ Неверный формат email")
                return
            data.setdefault("new_client_data", {})["email"] = text
            user_states[user_id] = UserState.CLIENT_REG_WAITING_INN
            await event.message.answer(
                f"✅ Email сохранён: {text}\n\n"
                "**Шаг 4/4 - ИНН** (необязательно)\n\nВведите ИНН или '-' чтобы пропустить:"
            )
            return
        
        if state == UserState.CLIENT_REG_WAITING_INN:
            if text == "-":
                data.setdefault("new_client_data", {})["inn"] = None
            elif validate_inn(text):
                data.setdefault("new_client_data", {})["inn"] = text
            else:
                await event.message.answer("❌ ИНН должен содержать 10 или 12 цифр")
                return
            
            client_data = data.get("new_client_data", {})
            buttons = [
                [CallbackButton(text="✅ Подтвердить", payload="confirm_client_reg", intent=Intent.POSITIVE)],
                [CallbackButton(text="❌ Отмена", payload="cancel_client_reg", intent=Intent.NEGATIVE)],
            ]
            attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
            text_msg = (
                "📋 **Подтверждение регистрации**\n\n"
                f"👤 ФИО: {client_data.get('full_name')}\n"
                f"📱 Телефон: {format_phone(client_data.get('phone'))}\n"
                f"📧 Email: {client_data.get('email')}\n"
                f"🆔 ИНН: {client_data.get('inn') or '—'}\n\n"
                "Всё верно?"
            )
            await event.message.answer(text_msg, attachments=[attachment])
            return
        
        # ДОБАВЛЕНИЕ КЛИЕНТА АГЕНТОМ
        if state == UserState.ADD_CLIENT_NAME:
            if len(text) < 2:
                await event.message.answer("❌ Имя слишком короткое")
                return
            data.setdefault("new_client", {})["full_name"] = text
            user_states[user_id] = UserState.ADD_CLIENT_PHONE
            await event.message.answer(
                f"✅ Имя сохранено: {text}\n\n"
                "**Шаг 2/5 - Телефон**\n\nВведите номер телефона:"
            )
            return
            
        # ===== ДОБАВЛЕНИЕ КЛИЕНТА АГЕНТОМ =====
        if state == UserState.ADD_CLIENT_NAME:
            await handle_add_client_name(event, user_id, chat_id, data, text)
            return
        
        if state == UserState.ADD_CLIENT_PHONE:
            await handle_add_client_phone(event, user_id, chat_id, data, text)
            return
        
        if state == UserState.ADD_CLIENT_EMAIL:
            await handle_add_client_email(event, user_id, chat_id, data, text)
            return
        
        if state == UserState.ADD_CLIENT_INN:
            await handle_add_client_inn(event, user_id, chat_id, data, text)
            return
        
        # Если состояние не найдено - игнорируем
        logger.warning(f"⚠️ Необработанное состояние: {state} для user_id={user_id}")


# ===== ОБРАБОТЧИКИ РЕГИСТРАЦИИ АГЕНТА =====

async def handle_reg_phone(event, user_id, chat_id, data, text):
    """Регистрация агента: телефон"""
    phone = normalize_phone(text)
    if not phone:
        await event.message.answer("❌ Неверный формат телефона")
        return
    
    reg_data = data.get("registration", {})
    reg_data["phone"] = phone
    user_states_ref = data.get("_user_states_ref")  # ссылка на словарь состояний
    
    # Переключаем состояние
    from states import UserState as US
    # Здесь нужно получить доступ к user_states из замыкания
    # Поэтому лучше передавать через параметры
    
    await event.message.answer(
        f"✅ Телефон сохранён: {phone}\n\n"
        "📧 **Шаг 2/3 - Email**\n\n"
        "Введите ваш email:"
    )


async def handle_reg_email(event, user_id, chat_id, data, text):
    """Регистрация агента: email"""
    if not validate_email(text):
        await event.message.answer("❌ Неверный формат email")
        return
    
    reg_data = data.get("registration", {})
    reg_data["email"] = text
    
    # Показываем выбор типа регистрации
    buttons = [
        [CallbackButton(text="👤 Самозанятый", payload="reg_type_self_employed", intent=Intent.DEFAULT)],
        [CallbackButton(text="📋 ИП", payload="reg_type_ip", intent=Intent.DEFAULT)],
        [CallbackButton(text="🏢 Юр. лицо", payload="reg_type_legal_entity", intent=Intent.DEFAULT)],
        [CallbackButton(text="❌ Отмена", payload="cancel_registration", intent=Intent.NEGATIVE)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    
    await event.message.answer(
        f"✅ Email сохранён: {text}\n\n"
        "🏷️ **Шаг 3/3 - Тип регистрации**",
        attachments=[attachment]
    )


# ===== ОБРАБОТЧИКИ РЕГИСТРАЦИИ КЛИЕНТА ПО РЕФЕРАЛКЕ =====

async def handle_client_name(event, user_id, chat_id, data, text):
    """Регистрация клиента: ФИО"""
    if len(text) < 2:
        await event.message.answer("❌ Имя слишком короткое")
        return
    
    client_data = data.get("new_client_data", {})
    client_data["full_name"] = text
    
    logger.info(f"✅ ФИО клиента сохранено: {text}")
    
    await event.message.answer(
        f"✅ ФИО сохранено: {text}\n\n"
        "**Шаг 2/4 - Телефон**\n\n"
        "Введите ваш номер телефона:"
    )


async def handle_client_phone(event, user_id, chat_id, data, text):
    """Регистрация клиента: телефон"""
    phone = normalize_phone(text)
    if not phone:
        await event.message.answer("❌ Неверный формат телефона")
        return
    
    # Проверяем существование
    existing = await api_client.get_client_by_phone(phone)
    if existing and not existing.get("error"):
        await event.message.answer(f"❌ Клиент с телефоном {phone} уже существует")
        return
    
    client_data = data.get("new_client_data", {})
    client_data["phone"] = phone
    
    await event.message.answer(
        f"✅ Телефон сохранён: {format_phone(phone)}\n\n"
        "**Шаг 3/4 - Email**\n\n"
        "Введите ваш email:"
    )


async def handle_client_email(event, user_id, chat_id, data, text):
    """Регистрация клиента: email"""
    if not validate_email(text):
        await event.message.answer("❌ Неверный формат email")
        return
    
    client_data = data.get("new_client_data", {})
    client_data["email"] = text
    
    await event.message.answer(
        f"✅ Email сохранён: {text}\n\n"
        "**Шаг 4/4 - ИНН** (необязательно)\n\n"
        "Введите ИНН или '-' чтобы пропустить:"
    )


async def handle_client_inn(event, user_id, chat_id, data, text):
    """Регистрация клиента: ИНН"""
    client_data = data.get("new_client_data", {})
    
    if text == "-":
        client_data["inn"] = None
    elif validate_inn(text):
        client_data["inn"] = text
    else:
        await event.message.answer("❌ ИНН должен содержать 10 или 12 цифр")
        return
    
    # Показываем подтверждение
    buttons = [
        [CallbackButton(text="✅ Подтвердить", payload="confirm_client_reg", intent=Intent.POSITIVE)],
        [CallbackButton(text="❌ Отмена", payload="cancel_client_reg", intent=Intent.NEGATIVE)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    
    text_msg = (
        "📋 **Подтверждение регистрации**\n\n"
        f"👤 ФИО: {client_data.get('full_name')}\n"
        f"📱 Телефон: {format_phone(client_data.get('phone'))}\n"
        f"📧 Email: {client_data.get('email')}\n"
        f"🆔 ИНН: {client_data.get('inn') or '—'}\n\n"
        "Всё верно?"
    )
    
    await event.message.answer(text_msg, attachments=[attachment])


# ===== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ КЛИЕНТА АГЕНТОМ =====

async def handle_add_client_name(event, user_id, chat_id, data, text):
    """Добавление клиента агентом: ФИО"""
    if len(text) < 2:
        await event.message.answer("❌ Имя слишком короткое")
        return
    
    client_data = data.get("new_client", {})
    client_data["full_name"] = text
    
    await event.message.answer(
        f"✅ Имя сохранено: {text}\n\n"
        "**Шаг 2/5 - Телефон**\n\n"
        "Введите номер телефона:"
    )


async def handle_add_client_phone(event, user_id, chat_id, data, text):
    """Добавление клиента агентом: телефон"""
    phone = normalize_phone(text)
    if not phone:
        await event.message.answer("❌ Неверный формат телефона")
        return
    
    existing = await api_client.get_client_by_phone(phone)
    if existing and not existing.get("error"):
        await event.message.answer(f"❌ Клиент с телефоном {phone} уже существует")
        return
    
    client_data = data.get("new_client", {})
    client_data["phone"] = phone
    
    await event.message.answer(
        f"✅ Телефон сохранён: {phone}\n\n"
        "**Шаг 3/5 - Email** (необязательно)\n\n"
        "Введите email или '-' чтобы пропустить:"
    )


async def handle_add_client_email(event, user_id, chat_id, data, text):
    """Добавление клиента агентом: email"""
    client_data = data.get("new_client", {})
    
    if text == "-":
        client_data["email"] = None
    elif validate_email(text):
        client_data["email"] = text
    else:
        await event.message.answer("❌ Неверный email")
        return
    
    await event.message.answer(
        "**Шаг 4/5 - ИНН** (необязательно)\n\n"
        "Введите ИНН или '-':"
    )


async def handle_add_client_inn(event, user_id, chat_id, data, text):
    """Добавление клиента агентом: ИНН"""
    client_data = data.get("new_client", {})
    
    if text == "-":
        client_data["inn"] = None
    elif validate_inn(text):
        client_data["inn"] = text
    else:
        await event.message.answer("❌ ИНН 10 или 12 цифр")
        return
    
    # Показываем выбор типа
    buttons = [
        [CallbackButton(text="👤 Физ. лицо", payload="client_type_individual", intent=Intent.DEFAULT)],
        [CallbackButton(text="🏢 Юр. лицо", payload="client_type_legal_entity", intent=Intent.DEFAULT)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    
    await event.message.answer("**Шаг 5/5 - Тип клиента**", attachments=[attachment])