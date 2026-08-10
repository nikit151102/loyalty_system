"""Роутер аутентификации"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import secrets

from auth import create_access_token, get_agent_by_user_id, get_client_by_phone, get_agent_by_phone
from database import get_session
from models.db_models import Application, ApplicationStatus, Agent, AgentStatus

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    phone: str
    role: Optional[str] = None  # "agent" | "client" | None

def generate_referral_code():
    return secrets.token_hex(4).upper()

@router.post("/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    phone = request.phone.strip()
    
    # === ПРИНУДИТЕЛЬНЫЙ ВЫБОР РОЛИ ===
    if request.role:
        if request.role == "agent":
            agent = await get_agent_by_phone(phone, session)
            if not agent:
                raise HTTPException(status_code=404, detail="Агент с таким телефоном не найден")
            
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
        
        elif request.role == "client":
            client = await get_client_by_phone(phone, session)
            if not client:
                raise HTTPException(status_code=404, detail="Клиент с таким телефоном не найден")
            
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
        
        else:
            raise HTTPException(status_code=400, detail="Некорректная роль. Используйте 'agent' или 'client'")
    
    # === АВТОМАТИЧЕСКАЯ ПРОВЕРКА ОБЕИХ ТАБЛИЦ ===
    client = await get_client_by_phone(phone, session)
    agent = await get_agent_by_phone(phone, session)
    
    # СЛУЧАЙ 1: Найдены и агент, и клиент — предлагаем выбор
    if agent and client:
        return {
            "status": "choose_role",
            "message": "Номер зарегистрирован и как агент, и как клиент. Выберите роль для входа.",
            "roles": ["agent", "client"],
            "agent_info": {
                "id": agent.id,
                "email": agent.email,
                "status": agent.status.value
            },
            "client_info": {
                "id": client.id,
                "full_name": client.full_name
            }
        }
    
    # СЛУЧАЙ 2: Только клиент
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
    
    # СЛУЧАЙ 3: Только агент
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
    
    # СЛУЧАЙ 4: Ищем ОДОБРЕННУЮ заявку
    app_result = await session.execute(
        select(Application).where(
            Application.phone == phone,
            Application.status == ApplicationStatus.APPROVED
        )
    )
    app = app_result.scalar_one_or_none()
    
    if app:
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
        app.agent_id = new_agent.id
        await session.commit()
        await session.refresh(new_agent)
        
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
    
    # СЛУЧАЙ 5: Никого не нашли
    raise HTTPException(status_code=404, detail="Пользователь с таким номером не найден. Требуется регистрация.")