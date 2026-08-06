"""Статистика"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent
from utils import format_money
from api_client import api_client

def register_statistics_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_callback(F.callback.payload == "statistics")
    async def show_stats(event: MessageCallback):
        await event.answer()
        user_id = event.callback.user.user_id
        chat_id = event.message.recipient.chat_id
        token = await api_client.login(user_id)
        if not token:
            await bot.send_message(chat_id=chat_id, text="❌ Нет доступа")
            return
        stats = await api_client.get_my_statistics(token)
        if not stats or stats.get("error"):
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка")
            return
        
        commission_by_rate = stats.get("commission_by_rate", {})
        rate_text = "".join(f"• {rate} — {count} операций\n" for rate, count in commission_by_rate.items()) or "Нет данных\n"
        
        top_clients = stats.get("top_clients", [])
        top_text = "".join(f"{i}. **{c['full_name']}** — {format_money(c['total_purchases_amount'])} ({c['purchases_count']})\n" for i, c in enumerate(top_clients, 1)) or "Нет клиентов\n"
        
        text = (
            f"📊 **Моя статистика**\n\n"
            f"💰 **Заработано:** {format_money(stats.get('total_commission_earned', 0))}\n"
            f"💳 **Баланс:** {format_money(stats.get('balance', 0))}\n"
            f"👥 **Клиентов:** {stats.get('total_clients', 0)}\n"
            f"🛍 **Оборот:** {format_money(stats.get('total_purchases_amount', 0))}\n"
            f"🔗 **Рефералов:** {stats.get('total_referrals', 0)}\n"
            f"   • 1 ур: {stats.get('level1_referrals', 0)}\n"
            f"   • 2 ур: {stats.get('level2_referrals', 0)}\n"
            f"📈 **Ср. комиссия:** {stats.get('average_commission_rate', 0)*100:.2f}%\n\n"
            f"**📊 По комиссиям:**\n{rate_text}\n"
            f"**⭐ Топ клиентов:**\n{top_text}"
        )
        buttons = [[CallbackButton(text="🏠 Назад", payload="agent_menu", intent=Intent.DEFAULT)]]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])