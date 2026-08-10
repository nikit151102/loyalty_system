"""Сервис клиентов"""
import io, base64
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import shortuuid, qrcode
from models.db_models import Client, ClientType, Agent
from config import settings


class ClientService:
    
    
    @staticmethod
    async def create_client(
        session: AsyncSession,
        agent_id: int,
        full_name: str,
        phone: str,
        email: Optional[str] = None,
        inn: Optional[str] = None,
        client_type: ClientType = ClientType.INDIVIDUAL,
        invited_by_client_id: Optional[int] = None,
        invited_by_agent_id: Optional[int] = None,
        max_user_id: Optional[int] = None,
        referral_code: Optional[str] = None  # НОВЫЙ ПАРАМЕТР
    ) -> Client:
        # Проверка на дубликат
        existing = (await session.execute(
            select(Client).where(Client.phone == phone)
        )).scalar_one_or_none()
        if existing:
            raise ValueError("Клиент с таким телефоном уже существует")
        
        # Генерируем QR-код (упрощённо)
        qr_base64 = await ClientService.generate_qr_code(phone)
        
        client = Client(
            agent_id=agent_id,
            full_name=full_name,
            phone=phone,
            email=email,
            inn=inn,
            client_type=client_type,
            qr_code_base64=qr_base64,
            referral_code=referral_code,  # СОХРАНЯЕМ REFERRAL CODE
            invited_by_client_id=invited_by_client_id,
            invited_by_agent_id=invited_by_agent_id,
            max_user_id=max_user_id,
            total_purchases_amount=0.0,
            purchases_count=0
        )
        
        session.add(client)
        await session.flush()
        return client
    
    @staticmethod
    async def generate_qr_code(data: str) -> str:
        """Генерация QR-кода в base64"""
        import qrcode
        import io
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    @staticmethod
    async def get_client_by_id(session: AsyncSession, client_id: int) -> Optional[Client]:
        return (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
    
    @staticmethod
    async def get_client_by_referral_code(session: AsyncSession, code: str) -> Optional[Client]:
        return (await session.execute(select(Client).where(Client.referral_code == code))).scalar_one_or_none()
    
    @staticmethod
    async def get_clients_by_agent(session: AsyncSession, agent_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[Client], int]:
        total = (await session.execute(select(func.count(Client.id)).where(Client.agent_id == agent_id))).scalar() or 0
        result = await session.execute(select(Client).where(Client.agent_id == agent_id).order_by(Client.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total
    
    @staticmethod
    async def update_client(session: AsyncSession, client_id: int, full_name=None, email=None, inn=None, client_type=None) -> Client:
        client = await ClientService.get_client_by_id(session, client_id)
        if not client: raise ValueError("Клиент не найден")
        if full_name: client.full_name = full_name
        if email is not None: client.email = email
        if inn is not None: client.inn = inn
        if client_type is not None: client.client_type = client_type
        from datetime import datetime
        client.updated_at = datetime.utcnow()
        await session.flush()
        return client
    
    @staticmethod
    async def delete_client(session: AsyncSession, client_id: int, agent_id: int) -> bool:
        result = await session.execute(select(Client).where(Client.id == client_id, Client.agent_id == agent_id))
        client = result.scalar_one_or_none()
        if not client: raise ValueError("Клиент не найден")
        await session.delete(client)
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent and agent.total_clients > 0: agent.total_clients -= 1
        await session.flush()
        return True