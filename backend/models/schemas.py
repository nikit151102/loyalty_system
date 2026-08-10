"""Pydantic схемы"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class AgentRegisterRequest(BaseModel):
    max_user_id: int
    phone: str
    email: EmailStr
    registration_type: str
    city: Optional[str]  = None
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^0-9+]", "", v)
        if clean.startswith("+") and len(clean) == 12: return clean
        if clean.startswith("8") and len(clean) == 11: return "+7" + clean[1:]
        if clean.startswith("7") and len(clean) == 11: return "+" + clean
        if clean.startswith("9") and len(clean) == 10: return "+7" + clean
        raise ValueError("Некорректный формат телефона")
    
    @field_validator("registration_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ["self_employed", "ip", "legal_entity"]:
            raise ValueError(f"Допустимые типы: self_employed, ip, legal_entity")
        return v


class AgentResponse(BaseModel):
    id: int
    max_user_id: int
    phone: str
    email: str
    city: Optional[str]  = None
    registration_type: str
    status: str
    referral_code: str
    balance: float
    total_clients: int
    total_purchases_amount: float
    total_commission_earned: float
    total_referrals_count: int
    created_at: datetime
    approved_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class AgentStatusResponse(BaseModel):
    status: str
    agent_id: Optional[int] = None
    is_approved: bool
    rejection_reason: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    max_user_id: int
    phone: str
    email: str
    registration_type: str
    status: str
    city: Optional[str]  = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class ClientCreateRequest(BaseModel):
    agent_id: int
    full_name: str = Field(..., min_length=2)
    phone: str
    email: Optional[EmailStr] = None
    inn: Optional[str] = None
    client_type: str = "individual"
    invited_by_client_id: Optional[int] = None
    invited_by_agent_id: Optional[int] = None
    max_user_id: Optional[int] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^0-9+]", "", v)
        if clean.startswith("+") and len(clean) == 12: return clean
        if clean.startswith("8") and len(clean) == 11: return "+7" + clean[1:]
        if clean.startswith("7") and len(clean) == 11: return "+" + clean
        if clean.startswith("9") and len(clean) == 10: return "+7" + clean
        raise ValueError("Некорректный формат телефона")
    
    @field_validator("inn")
    @classmethod
    def validate_inn(cls, v):
        if not v: return None
        clean = re.sub(r"[^0-9]", "", v)
        if len(clean) not in (10, 12): raise ValueError("ИНН 10 или 12 цифр")
        return clean


class ClientResponse(BaseModel):
    id: int
    agent_id: int
    full_name: str
    phone: str
    email: Optional[str] = None
    inn: Optional[str] = None
    client_type: str
    qr_code_base64: Optional[str] = None
    referral_code: Optional[str] = None
    total_purchases_amount: float
    purchases_count: int
    created_at: datetime
    max_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class ClientUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    inn: Optional[str] = None
    client_type: Optional[str] = None


class PurchaseCreateRequest(BaseModel):
    client_id: int
    amount: float = Field(..., gt=0)
    order_number: Optional[str] = None
    comment: Optional[str] = None
    added_by_user_id: Optional[int] = None


class PurchaseResponse(BaseModel):
    id: int
    client_id: int
    agent_id: int
    amount: float
    order_number: Optional[str] = None
    comment: Optional[str] = None
    commission_amount: float
    commission_rate: float
    created_at: datetime
    class Config:
        from_attributes = True

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ClientRegisterByReferralRequest(BaseModel):
    """Схема для регистрации клиента по реферальной ссылке"""
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None
    inn: Optional[str] = None
    client_type: str = "individual"
    referral_code: str = Field(..., description="Реферальный код агента (например, V9132513442)")


class ClientRegisterResponse(BaseModel):
    """Ответ с клиентом и токеном для автоматического входа"""
    client: 'ClientResponse'
    access_token: str
    token_type: str = "bearer"
    role: str = "client"