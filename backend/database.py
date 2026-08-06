"""Подключение к БД"""
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

sync_engine = create_engine(settings.database_url_sync, echo=settings.DEBUG)
async_engine = create_async_engine(settings.database_url_async, echo=settings.DEBUG)

SyncSession = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(class_=AsyncSession, autocommit=False, autoflush=False, bind=async_engine, expire_on_commit=False)

Base = declarative_base()


def create_db_if_not_exists():
    conn = None
    try:
        print(f"Проверка БД: {settings.POSTGRES_DB}")
        conn = psycopg2.connect(host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
                                user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD, dbname="postgres")
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (settings.POSTGRES_DB,))
        if cursor.fetchone():
            print(f"✓ БД {settings.POSTGRES_DB} уже существует")
        else:
            cursor.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}" ENCODING \'UTF8\'')
            print(f"✓ БД {settings.POSTGRES_DB} создана")
    except psycopg2.Error as e:
        print(f"✗ Ошибка БД: {e}")
    finally:
        if conn:
            cursor.close(); conn.close()


def create_tables():
    try:
        from models.db_models import Agent, Application, Client, Purchase, Commission, LoyaltyTransaction, Referral, AuditLog
        Base.metadata.create_all(bind=sync_engine)
        print("✓ Таблицы созданы")
    except Exception as e:
        print(f"✗ Ошибка создания таблиц: {e}")


async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()