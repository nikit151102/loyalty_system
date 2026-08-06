"""API клиент к FastAPI"""
import httpx
from typing import Optional, Dict
import logging
from config import config

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.api_key = config.API_KEY
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
    
    async def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.request(method, url, headers=self.headers, **kwargs)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            return {"error": e.response.text, "status_code": e.response.status_code}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
    
    async def _auth_request(self, method, path, token, **kwargs):
        url = f"{self.base_url}{path}"
        auth_headers = {**self.headers, "Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.request(method, url, headers=auth_headers, **kwargs)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            return {"error": e.response.text, "status_code": e.response.status_code}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
    
    async def register_agent(self, max_user_id, phone, email, reg_type, referral_code=None):
        data = {"max_user_id": max_user_id, "phone": phone, "email": email, "registration_type": reg_type}
        if referral_code: return await self._request("POST", f"/applications/register/{referral_code}", json=data)
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
    
    async def login(self, max_user_id):
        data = await self._request("POST", f"/auth/login?max_user_id={max_user_id}")
        if data and "access_token" in data: return data["access_token"]
        return None
    
    async def get_my_profile(self, token): return await self._auth_request("GET", "/agents/me", token)
    async def get_agent_status(self, token): return await self._auth_request("GET", "/agents/me/status", token)
    
    async def get_my_clients(self, token, skip=0, limit=20):
        data = await self._auth_request("GET", f"/clients/?skip={skip}&limit={limit}", token)
        return data if isinstance(data, list) else []
    
    async def get_client(self, token, client_id): return await self._auth_request("GET", f"/clients/{client_id}", token)
    async def add_client(self, token, client_data): return await self._auth_request("POST", "/clients/", token, json=client_data)
    async def update_client(self, token, client_id, data): return await self._auth_request("PATCH", f"/clients/{client_id}", token, json=data)
    async def delete_client(self, token, client_id): return await self._auth_request("DELETE", f"/clients/{client_id}", token)
    async def get_client_by_phone(self, phone): return await self._request("GET", f"/clients/by-phone/{phone}")
    async def get_client_by_referral(self, code): return await self._request("GET", f"/clients/by-referral/{code}")
    
    async def add_purchase(self, token, purchase_data): return await self._auth_request("POST", "/purchases/", token, json=purchase_data)
    async def get_client_purchases(self, token, client_id):
        data = await self._auth_request("GET", f"/purchases/client/{client_id}", token)
        return data if isinstance(data, list) else []
    
    async def get_my_commissions(self, token, skip=0, limit=50):
        data = await self._auth_request("GET", f"/commissions/?skip={skip}&limit={limit}", token)
        return data if data else {"items": [], "total": 0}
    
    async def get_my_transactions(self, token, skip=0, limit=50):
        data = await self._auth_request("GET", f"/commissions/transactions?skip={skip}&limit={limit}", token)
        return data if data else {"items": [], "total": 0}
    
    async def get_my_statistics(self, token): return await self._auth_request("GET", "/statistics/me", token)
    async def get_my_referral_info(self, token): return await self._auth_request("GET", "/referrals/me", token)

api_client = APIClient()