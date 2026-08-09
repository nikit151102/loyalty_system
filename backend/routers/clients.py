"""Роутер клиентов"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select
from auth import get_current_user, verify_api_key, get_agent_by_user_id
from database import get_session
from models.schemas import ClientCreateRequest, ClientResponse, ClientUpdateRequest, MessageResponse
from services.client_service import ClientService
from models.db_models import ClientType, Client
from fastapi.responses import Response
import base64


router = APIRouter(prefix="/clients", tags=["clients"])

@router.post("/", response_model=ClientResponse)
async def create_client(data: ClientCreateRequest, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        agent = await get_agent_by_user_id(int(payload.get("sub")), session)
        if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
        if data.agent_id != agent.id: raise HTTPException(status_code=403, detail="Нельзя добавить клиента другому агенту")
        
        client = await ClientService.create_client(
            session, data.agent_id, data.full_name, data.phone, data.email, data.inn, 
            ClientType(data.client_type), data.invited_by_client_id, data.invited_by_agent_id,
            max_user_id=data.max_user_id  
        )
        return ClientResponse.model_validate(client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/external", response_model=ClientResponse, dependencies=[Depends(verify_api_key)])
async def create_client_external(data: ClientCreateRequest, session: AsyncSession = Depends(get_session)):
    try:
        client = await ClientService.create_client(
            session, data.agent_id, data.full_name, data.phone, data.email, data.inn, 
            ClientType(data.client_type), data.invited_by_client_id, data.invited_by_agent_id,
            max_user_id=data.max_user_id  
        )
        return ClientResponse.model_validate(client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ClientResponse])
async def list_my_clients(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    clients, _ = await ClientService.get_clients_by_agent(session, agent.id, skip, limit)
    return [ClientResponse.model_validate(c) for c in clients]

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    client = await ClientService.get_client_by_id(session, client_id)
    if not client: raise HTTPException(status_code=404, detail="Клиент не найден")
    if client.agent_id != agent.id: raise HTTPException(status_code=403, detail="Нет доступа")
    return ClientResponse.model_validate(client)

@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(client_id: int, data: ClientUpdateRequest, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    client = await ClientService.get_client_by_id(session, client_id)
    if not client: raise HTTPException(status_code=404, detail="Клиент не найден")
    if client.agent_id != agent.id: raise HTTPException(status_code=403, detail="Нет доступа")
    updated = await ClientService.update_client(session, client_id, data.full_name, data.email, data.inn, ClientType(data.client_type) if data.client_type else None)
    return ClientResponse.model_validate(updated)

@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(client_id: int, payload: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    agent = await get_agent_by_user_id(int(payload.get("sub")), session)
    if not agent: raise HTTPException(status_code=403, detail="Доступ запрещён")
    try:
        await ClientService.delete_client(session, client_id, agent.id)
        return MessageResponse(message="Клиент удалён")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/by-phone/{phone}")
async def by_phone(phone: str, session: AsyncSession = Depends(get_session)):
    client = (await session.execute(select(Client).where(Client.phone == phone))).scalar_one_or_none()
    return ClientResponse.model_validate(client) if client else None

@router.get("/by-referral/{referral_code}", dependencies=[Depends(verify_api_key)])
async def by_referral(referral_code: str, session: AsyncSession = Depends(get_session)):
    client = await ClientService.get_client_by_referral_code(session, referral_code)
    return ClientResponse.model_validate(client) if client else None

@router.get("/{client_id}/qr", dependencies=[Depends(verify_api_key)])
async def get_client_qr_image(
    client_id: int,
    max_user_id: Optional[int] = Query(None, description="MAX User ID (если указан, игнорирует client_id)"),
    session: AsyncSession = Depends(get_session)
):
    """Вернуть QR-код клиента как PNG-изображение по client_id или max_user_id"""
    
    if max_user_id:
        client = (await session.execute(
            select(Client).where(Client.max_user_id == max_user_id)
        )).scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Клиент с таким max_user_id не найден")
    else:
        client = await ClientService.get_client_by_id(session, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")
    
    if not client.qr_code_base64:
        raise HTTPException(status_code=404, detail="QR-код не найден")
    
    qr_bytes = base64.b64decode(client.qr_code_base64)
    
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=qr_{client.referral_code}.png"
        }
    )