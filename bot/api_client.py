"""API клиент для связи с FastAPI backend + отправка сообщений через MAX API"""
import httpx
from typing import Optional, Dict, List
import logging
from config import config

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self):
        self.base_url = config.API_BASE_URL.rstrip("/")
        self.api_key = config.API_KEY
        # ✅ ДОБАВЛЕНО: атрибуты для MAX API
        self.max_api_url = "https://platform-api2.max.ru"
        self.max_bot_token = config.BOT_TOKEN
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
    
    # ===== ЗАПРОСЫ К BACKEND =====
    
    async def _request(self, method: str, path: str, **kwargs) -> Optional[Dict]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                r = await client.request(method, url, headers=self.headers, **kwargs)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            return {"error": e.response.text, "status_code": e.response.status_code}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
    
    async def _auth_request(self, method: str, path: str, token: str, **kwargs) -> Optional[Dict]:
        url = f"{self.base_url}{path}"
        auth_headers = {**self.headers, "Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                r = await client.request(method, url, headers=auth_headers, **kwargs)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            return {"error": e.response.text, "status_code": e.response.status_code}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
    
    # ===== ЗАЯВКИ =====
    async def register_agent(self, max_user_id, phone, email, reg_type, referral_code=None):
        data = {
            "max_user_id": max_user_id,
            "phone": phone,
            "email": email,
            "registration_type": reg_type,
        }
        if referral_code:
            return await self._request("POST", f"/applications/register/{referral_code}", json=data)
        return await self._request("POST", "/applications/register", json=data)
    
    async def get_application_status(self, max_user_id):
        return await self._request("GET", f"/applications/user/{max_user_id}")
    
    async def get_pending_applications(self, skip=0, limit=50):
        data = await self._request("GET", f"/applications/pending?skip={skip}&limit={limit}")
        return data if isinstance(data, list) else []
    
    async def approve_application(self, application_id, admin_user_id):
        return await self._request("PATCH", f"/applications/{application_id}/approve?reviewed_by={admin_user_id}")
    
    async def reject_application(self, application_id, admin_user_id, reason=None):
        url = f"/applications/{application_id}/reject?reviewed_by={admin_user_id}"
        if reason: url += f"&rejection_reason={reason}"
        return await self._request("PATCH", url)
    
    # ===== АГЕНТЫ =====
    async def login(self, max_user_id):
        data = await self._request("POST", f"/auth/login?max_user_id={max_user_id}")
        if data and "access_token" in data: return data["access_token"]
        return None
    
    async def get_my_profile(self, token):
        return await self._auth_request("GET", "/agents/me", token)
    
    async def get_agent_status(self, token):
        return await self._auth_request("GET", "/agents/me/status", token)
    
    async def get_agent_by_referral(self, code: str) -> Optional[Dict]:
        return await self._request("GET", f"/agents/by-referral/{code}")
    
    # ===== КЛИЕНТЫ =====
    async def get_my_clients(self, token, skip=0, limit=20):
        data = await self._auth_request("GET", f"/clients/?skip={skip}&limit={limit}", token)
        return data if isinstance(data, list) else []
    
    async def get_client(self, token, client_id):
        return await self._auth_request("GET", f"/clients/{client_id}", token)
    
    async def add_client(self, token, client_data):
        return await self._auth_request("POST", "/clients/", token, json=client_data)
    
    async def add_client_external(self, client_data: Dict) -> Optional[Dict]:
        """Создать клиента без JWT (для регистрации по рефералке)"""
        return await self._request("POST", "/clients/external", json=client_data)
    
    async def update_client(self, token, client_id, data):
        return await self._auth_request("PATCH", f"/clients/{client_id}", token, json=data)
    
    async def delete_client(self, token, client_id):
        return await self._auth_request("DELETE", f"/clients/{client_id}", token)
    
    async def get_client_by_phone(self, phone):
        return await self._request("GET", f"/clients/by-phone/{phone}")
    
    async def get_client_by_referral(self, code):
        return await self._request("GET", f"/clients/by-referral/{code}")
    
    # ===== ПОКУПКИ =====
    async def add_purchase(self, token, purchase_data):
        return await self._auth_request("POST", "/purchases/", token, json=purchase_data)
    
    async def get_client_purchases(self, token, client_id):
        data = await self._auth_request("GET", f"/purchases/client/{client_id}", token)
        return data if isinstance(data, list) else []
    
    # ===== КОМИССИИ =====
    async def get_my_commissions(self, token, skip=0, limit=50):
        data = await self._auth_request("GET", f"/commissions/?skip={skip}&limit={limit}", token)
        return data if data else {"items": [], "total": 0}
    
    async def get_my_transactions(self, token, skip=0, limit=50):
        data = await self._auth_request("GET", f"/commissions/transactions?skip={skip}&limit={limit}", token)
        return data if data else {"items": [], "total": 0}
    
    # ===== СТАТИСТИКА =====
    async def get_my_statistics(self, token):
        return await self._auth_request("GET", "/statistics/me", token)
    
    # ===== РЕФЕРАЛЫ =====
    async def get_my_referral_info(self, token):
        return await self._auth_request("GET", "/referrals/me", token)
    
    # ===== MAX API: ОТПРАВКА СООБЩЕНИЙ =====
    
    async def send_max_message(self, user_id: int, text: str, buttons: list = None) -> bool:
        """Отправить текстовое сообщение через MAX API"""
        url = f"{self.max_api_url}/messages?user_id={user_id}"
        
        headers = {
            "Authorization": self.max_bot_token,
            "Content-Type": "application/json"
        }
        
        payload = {"text": text}
        if buttons:
            payload["attachments"] = [{
                "type": "inline_keyboard",
                "payload": {"buttons": buttons}
            }]
        
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"✅ MAX сообщение отправлено user_id={user_id}")
                    return True
                logger.error(f"❌ MAX error: {response.status_code} - {response.text[:300]}")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка MAX: {e}")
            return False


async def send_qr_image(self, max_user_id: int, text: str = "", buttons: list = None) -> bool:
    """Отправить QR-код как картинку, используя прямую ссылку на backend по max_user_id"""
    backend_url = "http://192.54.100.195:6910" 
    
    # ✅ Передаём max_user_id как query-параметр, client_id ставим 0 (игнорируется)
    qr_image_url = f"{backend_url}/clients/0/qr?max_user_id={max_user_id}"
    
    logger.info(f"📷 Отправка QR по ссылке: {qr_image_url}")
    
    url = f"{self.max_api_url}/messages"
    headers = {
        "Authorization": self.max_bot_token,
        "Content-Type": "application/json"
    }
    
    attachments = [
        {
            "type": "image",
            "payload": {
                "url": qr_image_url
            }
        }
    ]
    
    if buttons:
        attachments.append({
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        })
    
    payload = {
        "text": text or " ",
        "attachments": attachments
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                params={"user_id": max_user_id}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ QR-картинка успешно отправлена max_user_id={max_user_id}")
                return True
            
            # Fallback на "photo", если "image" не сработал
            if response.status_code == 400:
                attachments[0]["type"] = "photo"
                payload["attachments"] = attachments
                response = await client.post(url, headers=headers, json=payload, params={"user_id": max_user_id})
                if response.status_code == 200:
                    return True
            
            logger.error(f"❌ Ошибка отправки: {response.status_code} - {response.text[:500]}")
            return False
    except Exception as e:
        logger.error(f"❌ Исключение: {e}")
        return False

api_client = APIClient()