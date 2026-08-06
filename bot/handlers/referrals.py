"""Рефералы"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from utils import format_money
from api_client import api_client

def register_referrals_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "referral")
    async def show_referral(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        ref = await api_client.get_my_referral_info(token)
        if not ref or ref.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка")
            return
        text = (
            f"🔗 **Реферальная программа**\n\n"
            f"**🔑 Код:** `{ref.get('referral_code')}`\n\n"
            f"**🔗 Ссылка:**\n`{ref.get('referral_link')}`\n\n"
            "**📊 Статистика:**\n"
            f"• Всего: {ref.get('total_invited', 0)}\n"
            f"• 1 ур: {ref.get('level1_count', 0)}\n"
            f"• 2 ур: {ref.get('level2_count', 0)}\n\n"
            "**💰 Бонусы:**\n"
            f"• Всего: {format_money(ref.get('total_bonus_earned', 0))}\n"
            f"• 1 ур (50%): {format_money(ref.get('level1_bonus', 0))}\n"
            f"• 2 ур (25%): {format_money(ref.get('level2_bonus', 0))}"
        )
        buttons = [[CallbackButton(text="🏠 Назад", payload="agent_menu", intent=Intent.DEFAULT)]]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])