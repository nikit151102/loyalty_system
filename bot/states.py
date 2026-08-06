"""Состояния FSM"""
from enum import Enum

class UserState(Enum):
    IDLE = "idle"
    REG_WAITING_PHONE = "reg_waiting_phone"
    REG_WAITING_EMAIL = "reg_waiting_email"
    REG_WAITING_TYPE = "reg_waiting_type"
    REG_CONFIRMATION = "reg_confirmation"
    ADD_CLIENT_NAME = "add_client_name"
    ADD_CLIENT_PHONE = "add_client_phone"
    ADD_CLIENT_EMAIL = "add_client_email"
    ADD_CLIENT_INN = "add_client_inn"
    ADD_CLIENT_TYPE = "add_client_type"
    ADD_CLIENT_CONFIRM = "add_client_confirm"
    ADD_PURCHASE_AMOUNT = "add_purchase_amount"
    ADD_PURCHASE_ORDER = "add_purchase_order"
    ADD_PURCHASE_COMMENT = "add_purchase_comment"
    ADD_PURCHASE_CONFIRM = "add_purchase_confirm"

REGISTRATION_TYPES = {"self_employed": "Самозанятый", "ip": "Индивидуальный предприниматель", "legal_entity": "Юридическое лицо"}
CLIENT_TYPES = {"individual": "Физическое лицо", "legal_entity": "Юридическое лицо"}