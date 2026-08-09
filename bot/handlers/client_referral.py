"""
Регистрация клиента по реферальной ссылке агента
Поток: рефералка → форма клиента → QR (картинка с backend) → [Стать агентом] → условия → заявка
"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from states import UserState
from utils import normalize_phone, validate_email, validate_inn, format_phone
from api_client import api_client
from config import config
import logging

logger = logging.getLogger(__name__)


def register_client_referral_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    # ===== НАЧАЛО РЕГИСТРАЦИИ КЛИЕНТА =====
    
    @dp.message_callback(F.callback.payload == "become_client")
    async def become_client_button(event: MessageCallback):
        """Начать регистрацию клиента по рефералке"""
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
        
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎁 **Регистрация клиента по приглашению**\n\n"
                 f"Вы приглашены агентом с кодом `{referral_code}`\n\n"
                 f"**Шаг 1/4 - ФИО**\n\n"
                 f"Введите ваше полное имя:"
        )
    
    # ===== ПОКАЗ QR-КОДА =====
    
    @dp.message_callback(F.callback.payload == "show_my_qr")
    async def show_my_qr(event: MessageCallback):
        """Показать QR-код клиента (картинкой через backend URL)"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        client_data = data.get("my_client_data")
        
        if not client_data:
            await bot.send_message(chat_id=chat_id, text="❌ Вы ещё не зарегистрированы как клиент.")
            return
        
        referral_code = client_data.get("referral_code", "")
        full_name = client_data.get("full_name", "Клиент")
        
        buttons = [
            [{"type": "callback", "text": "🚀 Стать агентом", "payload": "client_become_agent"}]
        ]
        
        # ✅ Используем max_user_id вместо client_id
        await api_client.send_qr_image(
            max_user_id=user_id,
            text=f"📱 Ваш QR-код клиента `{referral_code}`:",
            buttons=buttons
        )

    # ===== СТАТЬ АГЕНТОМ: УСЛОВИЯ =====
    
    @dp.message_callback(F.callback.payload == "client_become_agent")
    async def client_become_agent(event: MessageCallback):
        """Клиент хочет стать агентом — показываем условия"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        conditions_text = (
            "📋 **Условия агентской программы**\n\n"
            "💰 **Комиссии:**\n"
            "• 3% — при обороте до 100 000 ₽\n"
            "• 5% — при обороте свыше 100 000 ₽\n\n"
            "🔗 **Реферальная программа:**\n"
            "• 1 уровень: 50% от комиссии приглашённого агента\n"
            "• 2 уровень: 25% от комиссии агента 2-го уровня\n\n"
            "📊 **Что вы получаете:**\n"
            "• Личный кабинет со статистикой\n"
            "• Реферальную ссылку для приглашений\n"
            "• QR-коды для ваших клиентов\n"
            "• Автоматический расчёт комиссий\n\n"
            "⚠️ **Требования:**\n"
            "• Активная деятельность в программе\n"
            "• Соблюдение правил программы\n"
            "• Честное привлечение клиентов\n\n"
            "Готовы подать заявку?"
        )
        
        buttons = [
            [CallbackButton(text="📝 Подать заявку", payload="submit_agent_application", intent=Intent.POSITIVE)],
            [CallbackButton(text="⬅️ Назад", payload="back_to_client_menu", intent=Intent.DEFAULT)],
        ]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        
        await bot.send_message(chat_id=chat_id, text=conditions_text, attachments=[attachment])
    
    # ===== ПОДАТЬ ЗАЯВКУ АГЕНТА =====
    
    @dp.message_callback(F.callback.payload == "submit_agent_application")
    async def submit_agent_application(event: MessageCallback):
        """Начать форму регистрации агента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        
        referral_code = data.get("referral_code")
        if referral_code:
            data["registration"] = {"referral_code": referral_code}
            logger.info(f"📝 Подача заявки агента с рефералкой: {referral_code}")
        else:
            data["registration"] = {}
        
        user_states[user_id] = UserState.REG_WAITING_PHONE
        
        await bot.send_message(
            chat_id=chat_id,
            text="🚀 **Регистрация агента**\n\n"
                 "**Шаг 1/3 - Номер телефона**\n\n"
                 "Введите номер телефона:\n"
                 "Пример: +79991234567"
        )
    
    # ===== ВЕРНУТЬСЯ В МЕНЮ КЛИЕНТА =====
    
    @dp.message_callback(F.callback.payload == "back_to_client_menu")
    async def back_to_client_menu(event: MessageCallback):
        """Вернуться в меню клиента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        
        data = user_data.get(user_id, {})
        client_data = data.get("my_client_data")
        
        if client_data:
            await show_client_menu_with_qr(bot, user_id, chat_id, client_data)
        else:
            from handlers.start import send_start_menu
            await send_start_menu(bot, chat_id, "друг")
    
    # ===== ОТМЕНА РЕГИСТРАЦИИ КЛИЕНТА =====
    
    @dp.message_callback(F.callback.payload == "cancel_client_reg")
    async def cancel_client_reg(event: MessageCallback):
        """Отменить регистрацию клиента"""
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        user_states[user_id] = UserState.IDLE
        
        from handlers.start import send_start_menu
        await send_start_menu(bot, chat_id, "друг")
    
    # ===== ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ КЛИЕНТА =====
    
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
        
        # ✅ ДОБАВЛЕНО: max_user_id в payload
        payload = {
            "agent_id": agent_info["id"],
            "full_name": client_data.get("full_name"),
            "phone": client_data.get("phone"),
            "email": client_data.get("email"),
            "inn": client_data.get("inn"),
            "client_type": "individual",
            "invited_by_agent_id": agent_info["id"],
            "max_user_id": user_id  # <-- ВАЖНО: привязываем клиента к MAX user_id
        }
        
        result = await api_client.add_client_external(payload)
        
        if result and not result.get("error"):
            user_states[user_id] = UserState.IDLE
            
            data["my_client_data"] = result
            data["is_client"] = True
            
            referral_code = result.get("referral_code", "")
            full_name = result.get("full_name", "Клиент")
            
            buttons = [
                [{"type": "callback", "text": "📱 Показать QR ещё раз", "payload": "show_my_qr"}],
                [{"type": "callback", "text": "🚀 Стать агентом", "payload": "client_become_agent"}]
            ]
            
            text_msg = (
                f"🎉 Добро пожаловать, {full_name}!\n\n"
                f"✅ Вы успешно зарегистрированы как клиент.\n"
                f"🔑 Ваш код: `{referral_code}`\n\n"
                f"Ваш QR-код отправлен ниже 👇"
            )
            
            # ✅ ОТПРАВЛЯЕМ КАРТИНКУ ЧЕРЕЗ ПРЯМУЮ ССЫЛКУ НА BACKEND
            success = await api_client.send_qr_image(
                max_user_id=user_id,
                text=text_msg,
                buttons=buttons
            )
            
            if not success:
                backend_url = "http://192.54.100.195:6910"
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🎉 Добро пожаловать, {full_name}!\n\n"
                        f"✅ Вы успешно зарегистрированы как клиент.\n"
                        f"🔑 Ваш код: `{referral_code}`\n\n"
                        f"📱 К сожалению, не удалось отправить картинку.\n"
                        f"Ваш QR-код доступен по ссылке:\n{backend_url}/clients/0/qr?max_user_id={user_id}"
                    )
                )
        else:
            err = result.get("error", "Неизвестная ошибка") if result else "Ошибка соединения"
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {err}")

    # ===== ОБРАБОТКА ТЕКСТА ПРИ РЕГИСТРАЦИИ КЛИЕНТА =====
    
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
            
            existing = await api_client.get_client_by_phone(phone)
            if existing and not existing.get("error"):
                await event.message.answer(f"❌ Клиент с телефоном {phone} уже существует")
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


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

async def show_client_menu_with_qr(bot, user_id: int, chat_id: int, client_data: dict):
    """Показать меню клиента с кнопками"""
    full_name = client_data.get("full_name", "")
    referral_code = client_data.get("referral_code", "")
    
    text = (
        f"🎉 **Добро пожаловать, {full_name}!**\n\n"
        f"✅ Вы успешно зарегистрированы как клиент\n\n"
        f"🔑 **Ваш код клиента:** `{referral_code}`\n\n"
        f"💰 Вам будет начисляться кэшбэк с покупок!\n\n"
        f"Используйте кнопки ниже:"
    )
    
    buttons = [
        [CallbackButton(text="📱 Показать QR-код", payload="show_my_qr", intent=Intent.DEFAULT)],
        [CallbackButton(text="🚀 Стать агентом", payload="client_become_agent", intent=Intent.POSITIVE)],
    ]
    attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
    
    await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])