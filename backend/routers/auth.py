"""Роутер аутентификации"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import secrets

from auth import create_access_token, get_agent_by_user_id, get_client_by_phone, get_agent_by_phone
from database import get_session
from models.db_models import Application, ApplicationStatus, Agent, AgentStatus

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    phone: str

def generate_referral_code():
    return secrets.token_hex(4).upper() # Генерирует 8 символов, например 'A1B2C3D4'

@router.post("/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    phone = request.phone.strip()
    
    # 1. Сначала ищем в таблице клиентов
    client = await get_client_by_phone(phone, session)
    if client:
        token_data = {
            "sub": str(client.max_user_id if client.max_user_id else client.id),
            "user_id": client.id,
            "role": "client"
        }
        token = create_access_token(data=token_data)
        return {
            "access_token": token, 
            "token_type": "bearer",
            "role": "client",
            "user_id": client.id
        }

    # 2. Если клиент не найден, ищем в таблице агентов
    agent = await get_agent_by_phone(phone, session)
    if agent:
        token_data = {
            "sub": str(agent.max_user_id),
            "user_id": agent.id,
            "role": "agent",
            "status": agent.status.value
        }
        token = create_access_token(data=token_data)
        return {
            "access_token": token, 
            "token_type": "bearer",
            "role": "agent",
            "user_id": agent.id,
            "status": agent.status.value
        }

    # 3. НОВОЕ: Ищем ОДОБРЕННУЮ заявку
    app_result = await session.execute(
        select(Application).where(
            Application.phone == phone, 
            Application.status == ApplicationStatus.APPROVED
        )
    )
    app = app_result.scalar_one_or_none()
    
    if app:
        # Заявка одобрена, но агент еще не создан. Создаем его автоматически!
        new_agent = Agent(
            max_user_id=app.max_user_id,
            phone=app.phone,
            email=app.email,
            registration_type=app.registration_type,
            status=AgentStatus.ACTIVE,
            referral_code=generate_referral_code(),
            balance=0.0, 
            total_clients=0, 
            total_purchases_amount=0.0,
            total_commission_earned=0.0, 
            total_referrals_count=0
        )
        session.add(new_agent)
        
        # Связываем заявку с новым агентом
        app.agent_id = new_agent.id 
        
        await session.commit()
        await session.refresh(new_agent)
        
        # Возвращаем токен для только что созданного агента
        token_data = {
            "sub": str(new_agent.max_user_id), 
            "user_id": new_agent.id, 
            "role": "agent", 
            "status": new_agent.status.value
        }
        token = create_access_token(data=token_data)
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "role": "agent", 
            "user_id": new_agent.id, 
            "status": new_agent.status.value
        }

    # 4. Никого не нашли — фронтенд поймет, что нужна регистрация
    raise HTTPException(status_code=404, detail="Пользователь с таким номером не найден. Требуется регистрация.")