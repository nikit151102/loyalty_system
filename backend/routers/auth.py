"""Роутер аутентификации"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from auth import create_access_token, get_agent_by_user_id
from database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(max_user_id: int, session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(max_user_id, session)
    if not agent: raise HTTPException(status_code=404, detail="Агент не найден")
    token = create_access_token(data={"sub": str(agent.max_user_id), "agent_id": agent.id})
    return {"access_token": token, "token_type": "bearer"}