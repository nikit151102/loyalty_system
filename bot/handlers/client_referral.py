"""
Регистрация клиента по реферальной ссылке агента
Поток: рефералка → форма клиента → QR → кнопка "Стать агентом"
"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState
from utils import normalize_phone, validate_email, validate_inn, format_phone
from api_client import api_client
import logging
import base64

logger = logging.getLogger(__name__)


def register_client_referral_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "become_client")
    async def become_client_button(event: MessageCallback):
        """Начать регистрацию клиента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        referral_code = data.get("referral_code")
        agent_info = data.get("referrer_agent_info")
        
        if not referral_code or not agent_info:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Реферальный код не найден. Попробуйте перейти по ссылке ещё раз."
            )
            return
        
        user_states[user_id] = UserState.CLIENT_REG_WAITING_NAME
        data["new_client_data"] = {}
        
        agent_name = agent_info.get("referral_code", "агент")
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎁 **Регистрация клиента по приглашению**\n\n"
                 f"Вы приглашены агентом с кодом `{referral_code}`\n\n"
                 f"**Шаг 1/4 - ФИО**\n\n"
                 f"Введите ваше полное имя:"
        )
    
    @dp.message_callback(F.callback.payload == "cancel_client_reg")
    async def cancel_client_reg(event: MessageCallback):
        """Отменить регистрацию клиента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        user_states[user_id] = UserState.IDLE
        
        from handlers.start import send_start_menu
        await send_start_menu(bot, chat_id, "друг")
    
    @dp.message_callback(F.callback.payload == "confirm_client_reg")
    async def confirm_client_registration(event: MessageCallback):
        """Подтвердить регистрацию клиента и создать в БД"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        client_data = data.get("new_client_data", {})
        agent_info = data.get("referrer_agent_info", {})
        
        if not agent_info.get("id"):
            await bot.send_message(chat_id=chat_id, text="❌ Агент не найден. Попробуйте заново.")
            return
        
        # Создаём клиента через API
        payload = {
            "agent_id": agent_info["id"],  # ← агент из реферального кода
            "full_name": client_data.get("full_name"),
            "phone": client_data.get("phone"),
            "email": client_data.get("email"),
            "inn": client_data.get("inn"),
            "client_type": "individual",
            "invited_by_agent_id": agent_info["id"],  # ← кто пригласил
        }
        
        result = await api_client.add_client_external(payload)  # без JWT
        
        if result and not result.get("error"):
            user_states[user_id] = UserState.IDLE
            
            # Сохраняем данные клиента для дальнейшего использования
            data["my_client_data"] = result
            data["is_client"] = True
            
            # Показываем QR-код
            await show_client_qr_and_menu(bot, chat_id, result)
        else:
            err = result.get("error", "Неизвестная ошибка") if result else "Ошибка соединения"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")
    
    @dp.message_callback(F.callback.payload == "client_become_agent")
    async def client_become_agent(event: MessageCallback):
        """Клиент хочет стать агентом"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        
        # Если есть реферальный код — передаём его
        referral_code = data.get("referral_code")
        if referral_code:
            data["registration"] = {"referral_code": referral_code}
        else:
            data["registration"] = {}
        
        user_states[user_id] = UserState.REG_WAITING_PHONE
        
        await bot.send_message(
            chat_id=chat_id,
            text="🚀 **Стать агентом**\n\n"
                 "Заполните форму для регистрации агента:\n\n"
                 "**Шаг 1/3 - Номер телефона**\n\n"
                 "Введите номер телефона:\n"
                 "Пример: +79991234567"
        )
    
    @dp.message_callback(F.callback.payload == "show_my_qr")
    async def show_my_qr(event: MessageCallback):
        """Показать QR-код клиента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        client_data = data.get("my_client_data")
        
        if not client_data:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Вы ещё не зарегистрированы как клиент."
            )
            return
        
        await show_client_qr_and_menu(bot, chat_id, client_data)
    
    @dp.message_created(F.message.body.text)
    async def handle_client_reg_text(event: MessageCreated):
        """Обработка текстового ввода при регистрации клиента"""
        text = event.message.body.text.strip()
        user_id = event.message.sender.user_id
        chat_id = event.message.recipient.chat_id
        
        if text.startswith("/"):
            return
        
        state = user_states.get(user_id)
        data = user_data.get(user_id, {})
        client_data = data.get("new_client_data", {})
        
        # Шаг 1: ФИО
        if state == UserState.CLIENT_REG_WAITING_NAME:
            if len(text) < 2:
                await event.message.answer("❌ Имя слишком короткое")
                return
            client_data["full_name"] = text
            user_states[user_id] = UserState.CLIENT_REG_WAITING_PHONE
            await event.message.answer(
                f"✅ ФИО сохранено: {text}\n\n"
                "**Шаг 2/4 - Телефон**\n\n"
                "Введите ваш номер телефона:"
            )
            return
        
        # Шаг 2: Телефон
        if state == UserState.CLIENT_REG_WAITING_PHONE:
            phone = normalize_phone(text)
            if not phone:
                await event.message.answer("❌ Неверный формат телефона")
                return
            
            # Проверяем, не существует ли клиент с таким телефоном
            existing = await api_client.get_client_by_phone(phone)
            if existing and not existing.get("error"):
                await event.message.answer(
                    f"❌ Клиент с телефоном {phone} уже существует"
                )
                return
            
            client_data["phone"] = phone
            user_states[user_id] = UserState.CLIENT_REG_WAITING_EMAIL
            await event.message.answer(
                f"✅ Телефон сохранён: {format_phone(phone)}\n\n"
                "**Шаг 3/4 - Email**\n\n"
                "Введите ваш email:"
            )
            return
        
        # Шаг 3: Email
        if state == UserState.CLIENT_REG_WAITING_EMAIL:
            if not validate_email(text):
                await event.message.answer("❌ Неверный формат email")
                return
            client_data["email"] = text
            user_states[user_id] = UserState.CLIENT_REG_WAITING_INN
            await event.message.answer(
                f"✅ Email сохранён: {text}\n\n"
                "**Шаг 4/4 - ИНН** (необязательно)\n\n"
                "Введите ИНН или '-' чтобы пропустить:"
            )
            return
        
        # Шаг 4: ИНН
        if state == UserState.CLIENT_REG_WAITING_INN:
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
            return


async def show_client_qr_and_menu(bot, chat_id: int, client_data: dict):
    """Показать QR-код клиента и меню действий"""
    
    referral_code = client_data.get("referral_code", "")
    full_name = client_data.get("full_name", "")
    
    text = (
        f"🎉 **Добро пожаловать, {full_name}!**\n\n"
        f"✅ Вы успешно зарегистрированы как клиент\n\n"
        f"🔑 **Ваш код клиента:** `{referral_code}`\n\n"
        f"📱 **QR-код отправлен ниже** — покажите его при покупке\n\n"
        f"💰 Вам будет начисляться кэшбэк с покупок!"
    )
    
    buttons = [
        [CallbackButton(text="🎁 Стать агентом", payload="client_become_agent", intent=Intent.POSITIVE)],
        [CallbackButton(text="📱 Показать QR ещё раз", payload="show_my_qr", intent=Intent.DEFAULT)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    
    await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])
    
    # Отправляем QR-код как фото (если есть)
    qr_base64 = client_data.get("qr_code_base64")
    if qr_base64:
        try:
            from maxapi.types import Attachment as PhotoAttachment
            
            # Декодируем base64 в файл
            qr_bytes = base64.b64decode(qr_base64)
            
            # Отправляем как фото
            photo_attachment = PhotoAttachment(
                type="photo",
                payload={"base64": qr_base64}  # формат зависит от maxapi
            )
            
            await bot.send_message(
                chat_id=chat_id,
                text="📱 Ваш QR-код:",
                attachments=[photo_attachment]
            )
        except Exception as e:
            logger.error(f"Ошибка отправки QR: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"📱 QR-код (в формате base64): {qr_base64[:100]}..."
            )