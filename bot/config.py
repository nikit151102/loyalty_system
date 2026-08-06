"""Конфиг бота"""
import os
from dotenv import load_dotenv
load_dotenv()

class BotConfig:
    BOT_TOKEN: str = "f9LHodD0cOItvPIlwo5bsHYP41dZqM45Pnjuwt48tlZ7DNKnw-6_UeB6gaOqk63eIaLJhutpEGnGSe7YKPHz"
    BOT_NAME: str = os.getenv("MAX_BOT_NAME", "")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:6410")
    API_KEY: str = os.getenv("API_KEY", "bot_api_key")
    ADMIN_USER_IDS: str = os.getenv("ADMIN_USER_IDS", "")
    BASE_REFERRAL_URL: str = os.getenv("BASE_REFERRAL_URL", "https://max.ru/your_bot")
    
    @property
    def admin_ids(self):
        if not self.ADMIN_USER_IDS: return []
        try: return [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",") if x.strip()]
        except: return []

config = BotConfig()