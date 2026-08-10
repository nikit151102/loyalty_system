"""Роутер аутентификации"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from auth import create_access_token, get_agent_by_user_id, get_client_by_phone, get_agent_by_phone
from database import get_session
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    phone: str

@router.post("/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    phone = request.phone.strip()
    
    # 1. Сначала ищем в таблице клиентов
    client = await get_client_by_phone(phone, session)
    if client:
        token_data = {
            "sub": str(client.max_user_id if client.max_user_id else client.id), # sub для совместимости
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
            "status": agent.status.value # Передаем статус, чтобы фронт знал, активен ли агент
        }
        token = create_access_token(data=token_data)
        return {
            "access_token": token, 
            "token_type": "bearer",
            "role": "agent",
            "user_id": agent.id,
            "status": agent.status.value
        }

    # 3. Никого не нашли — фронтенд поймет, что нужна регистрация
    raise HTTPException(status_code=404, detail="Пользователь с таким номером не найден. Требуется регистрация.")