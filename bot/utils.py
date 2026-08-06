"""Утилиты"""
import re
from typing import Optional

def normalize_phone(phone: str) -> Optional[str]:
    clean = re.sub(r"[^0-9+]", "", phone)
    if clean.startswith("+") and len(clean) == 12: return clean
    if clean.startswith("8") and len(clean) == 11: return "+7" + clean[1:]
    if clean.startswith("7") and len(clean) == 11: return "+" + clean
    if clean.startswith("9") and len(clean) == 10: return "+7" + clean
    return None

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

def validate_inn(inn: str) -> bool:
    return len(re.sub(r"[^0-9]", "", inn)) in (10, 12)

def format_money(amount: float) -> str:
    if amount >= 1_000_000: return f"{amount/1_000_000:.2f} млн ₽"
    if amount >= 1000: return f"{amount/1000:.2f} тыс ₽"
    return f"{amount:.2f} ₽"

def format_phone(phone: str) -> str:
    clean = re.sub(r"[^0-9]", "", phone)
    if len(clean) == 11: return f"+{clean[0]} ({clean[1:4]}) {clean[4:7]}-{clean[7:9]}-{clean[9:11]}"
    return phone