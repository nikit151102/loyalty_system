"""Главный MAX бот"""
import sys, os, asyncio, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from maxapi import Bot, Dispatcher
from config import config
from api_client import api_client

# Импорты хендлеров
from handlers.start import register_start_handlers
from handlers.registration import register_registration_handlers
from handlers.status import register_status_handlers
from handlers.agent_menu import register_agent_menu_handlers
from handlers.clients import register_clients_handlers
from handlers.statistics import register_statistics_handlers
from handlers.referrals import register_referrals_handlers
from handlers.admin import register_admin_handlers
from handlers.help import register_help_handlers
from handlers.client_referral import register_client_referral_handlers
from handlers.text_router import register_text_router  # ← ЭТА СТРОКА БЫЛА ПРОПУЩЕНА

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LoyaltyBot:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher()
        self.user_states = {}
        self.user_data = {}
        self._register_all_handlers()
    
    def _register_all_handlers(self):
        register_start_handlers(self.dp, self.bot, self.user_states, self.user_data, api_client)
        register_registration_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_status_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_agent_menu_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_clients_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_statistics_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_referrals_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_admin_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_help_handlers(self.dp, self.bot, self.user_states, self.user_data)
        register_client_referral_handlers(self.dp, self.bot, self.user_states, self.user_data)
        
        # ✅ Единый роутер текстовых сообщений
        register_text_router(self.dp, self.bot, self.user_states, self.user_data)
    
    async def run(self):
        logger.info("🤖 MAX-бот запускается...")
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"✓ Бот: @{getattr(bot_info, 'username', 'N/A')}")
        except Exception as e:
            logger.warning(f"Не удалось получить инфо: {e}")
        try:
            await self.bot.delete_webhook()
            logger.info("✓ Webhook удалён")
        except Exception as e:
            logger.warning(f"Ошибка webhook: {e}")
        logger.info("✓ MAX-бот запущен")
        await self.dp.start_polling(self.bot)


async def main():
    logger.info("=" * 50)
    logger.info("Запуск MAX-бота программы лояльности")
    logger.info("=" * 50)
    if not config.BOT_TOKEN:
        logger.error("❌ MAX_BOT_TOKEN не задан!")
        return
    bot = LoyaltyBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()