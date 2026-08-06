"""Помощь"""
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, MessageCallback, Command, CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent

def register_help_handlers(dp: Dispatcher, bot, user_states, user_data):
    
    @dp.message_created(Command("help"))
    async def cmd_help(event: MessageCreated):
        await send_help(bot, event.message.recipient.chat_id)
    
    @dp.message_callback(F.callback.payload == "help")
    async def help_btn(event: MessageCallback):
        await event.answer()
        await send_help(bot, event.message.recipient.chat_id)
    
    async def send_help(bot, chat_id):
        text = (
            "❓ **Справка**\n\n"
            "**Как это работает:**\n"
            "1. Подайте заявку и дождитесь одобрения\n"
            "2. Добавляйте клиентов через бота\n"
            "3. Получайте комиссию за их покупки\n"
            "4. Приглашайте других агентов за бонусами\n\n"
            "**💰 Комиссии:**\n"
            "• 3% — до 100 000 ₽ оборота\n"
            "• 5% — свыше 100 000 ₽\n\n"
            "**🔗 Реферальная программа:**\n"
            "• 1 уровень: 50% комиссии\n"
            "• 2 уровень: 25% комиссии"
        )
        buttons = [[CallbackButton(text="🏠 Назад", payload="back_to_start", intent=Intent.DEFAULT)]]
        attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=buttons))
        await bot.send_message(chat_id=chat_id, text=text, attachments=[attachment])