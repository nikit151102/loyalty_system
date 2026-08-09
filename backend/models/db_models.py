"""Модели БД"""
import enum
from sqlalchemy import (Column, Integer, String, Float, Boolean, DateTime, Text,
                        Enum, ForeignKey, BigInteger)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RegistrationType(str, enum.Enum):
    SELF_EMPLOYED = "self_employed"
    INDIVIDUAL_ENTREPRENEUR = "ip"
    LEGAL_ENTITY = "legal_entity"


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    INACTIVE = "inactive"


class ClientType(str, enum.Enum):
    INDIVIDUAL = "individual"
    LEGAL_ENTITY = "legal_entity"


class TransactionType(str, enum.Enum):
    ACCRUAL = "accrual"
    WITHDRAWAL = "withdrawal"
    CORRECTION = "correction"
    REFERRAL_BONUS = "referral_bonus"


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    max_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    registration_type = Column(Enum(RegistrationType), nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False)
    referral_code = Column(String(32), unique=True, nullable=False, index=True)
    invited_by_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    balance = Column(Float, default=0.0, nullable=False)
    total_clients = Column(Integer, default=0, nullable=False)
    total_purchases_amount = Column(Float, default=0.0, nullable=False)
    total_commission_earned = Column(Float, default=0.0, nullable=False)
    total_referrals_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    approved_at = Column(DateTime, nullable=True)

    application = relationship("Application", back_populates="agent", uselist=False)
    
    # ИСПРАВЛЕНО: Указано имя класса Client
    clients = relationship("Client", back_populates="agent", foreign_keys="[Client.agent_id]", cascade="all, delete-orphan")
    
    purchases = relationship("Purchase", back_populates="agent", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="agent", cascade="all, delete-orphan")
    transactions = relationship("LoyaltyTransaction", back_populates="agent", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="agent", cascade="all, delete-orphan")
    
    # ИСПРАВЛЕНО: Указано имя класса Referral
    referral_invited = relationship("Referral", back_populates="inviter_agent", foreign_keys="[Referral.inviter_agent_id]")


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), unique=True, nullable=True)
    max_user_id = Column(BigInteger, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    registration_type = Column(Enum(RegistrationType), nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    agent = relationship("Agent", back_populates="application")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    inn = Column(String(20), nullable=True, index=True)
    client_type = Column(Enum(ClientType), default=ClientType.INDIVIDUAL, nullable=False)
    qr_code_base64 = Column(Text, nullable=True)
    referral_code = Column(String(32), unique=True, nullable=True, index=True)
    total_purchases_amount = Column(Float, default=0.0, nullable=False)
    purchases_count = Column(Integer, default=0, nullable=False)
    invited_by_client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    invited_by_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    is_agent = Column(Boolean, default=False, nullable=False)
    
    max_user_id = Column(BigInteger, nullable=True, index=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    agent = relationship("Agent", back_populates="clients", foreign_keys="[Client.agent_id]")
    purchases = relationship("Purchase", back_populates="client", cascade="all, delete-orphan")

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    order_number = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    added_by_user_id = Column(BigInteger, nullable=True)
    commission_amount = Column(Float, default=0.0, nullable=False)
    commission_rate = Column(Float, default=0.0, nullable=False)
    referral_bonus_level1 = Column(Float, default=0.0, nullable=False)
    referral_bonus_level2 = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    client = relationship("Client", back_populates="purchases")
    agent = relationship("Agent", back_populates="purchases")
    commission = relationship("Commission", back_populates="purchase", uselist=False, cascade="all, delete-orphan")


class Commission(Base):
    __tablename__ = "commissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    referral_level = Column(Integer, default=0, nullable=False)  # 0=прямая, 1=1 ур., 2=2 ур.
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    agent = relationship("Agent", back_populates="commissions")
    purchase = relationship("Purchase", back_populates="commission")


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    commission_id = Column(Integer, ForeignKey("commissions.id"), nullable=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    agent = relationship("Agent", back_populates="transactions")


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    inviter_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    invited_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, unique=True)
    level = Column(Integer, nullable=False, default=1)  # 1 или 2
    invited_turnover = Column(Float, default=0.0, nullable=False)
    total_bonus_earned = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # ИСПРАВЛЕНО: Указано имя класса Referral
    inviter_agent = relationship("Agent", foreign_keys="[Referral.inviter_agent_id]", back_populates="referral_invited")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    agent = relationship("Agent", back_populates="audit_logs")