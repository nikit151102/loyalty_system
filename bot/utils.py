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


def generate_qr_bytes(data: str, client_name: str = "", client_code: str = "") -> bytes:
    """Генерирует красивый QR-код с подписью и возвращает PNG bytes."""
    import io
    import logging
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    
    logger = logging.getLogger(__name__)
    logger.info(f"🎨 Генерация QR для: {data[:50]}...")
    
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    
    padding_top = 20
    padding_bottom = 80
    padding_side = 20
    
    final_width = qr_img.width + padding_side * 2
    final_height = qr_img.height + padding_top + padding_bottom
    
    final_img = Image.new("RGB", (final_width, final_height), "white")
    final_img.paste(qr_img, (padding_side, padding_top))
    
    draw = ImageDraw.Draw(final_img)
    
    try:
        try:
            title_font = ImageFont.truetype("arial.ttf", 20)
            code_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            code_font = ImageFont.load_default()
        
        if client_name:
            draw.text(
                (final_width // 2, qr_img.height + padding_top + 10),
                client_name, fill="black", font=title_font, anchor="mt"
            )
        if client_code:
            draw.text(
                (final_width // 2, qr_img.height + padding_top + 40),
                f"Код: {client_code}", fill="gray", font=code_font, anchor="mt"
            )
    except Exception as e:
        logger.warning(f"Не удалось добавить подпись: {e}")
    
    buffer = io.BytesIO()
    final_img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    
    photo_bytes = buffer.getvalue()
    logger.info(f"✅ QR сгенерирован: {len(photo_bytes)} bytes, {final_width}x{final_height}")
    
    return photo_bytes

