"""Конфигурация backend"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Loyalty API Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:6410")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change_me")
    API_KEY: str = os.getenv("API_KEY", "bot_api_key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "root")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "loyalty_db")
    
    ADMIN_USER_IDS: str = os.getenv("ADMIN_USER_IDS", "")
    BASE_REFERRAL_URL: str = os.getenv("BASE_REFERRAL_URL", "https://max.ru/your_bot")
    
    COMMISSION_RATE_LOW: float = 0.03
    COMMISSION_RATE_HIGH: float = 0.05
    COMMISSION_THRESHOLD: float = 100000.0
    
    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_USER_IDS: return []
        try: return [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",") if x.strip()]
        except: return []
    
    @property
    def database_url_sync(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def database_url_async(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"


settings = Settings()