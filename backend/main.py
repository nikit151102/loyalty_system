"""Главный FastAPI"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import create_db_if_not_exists, create_tables
from routers import auth, agents, applications, clients, purchases, commissions, statistics, referrals, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Запуск {settings.APP_NAME} v{settings.APP_VERSION}")
    create_db_if_not_exists()
    create_tables()
    print("✅ Backend готов")
    yield
    print("👋 Backend остановлен")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(applications.router)
app.include_router(clients.router)
app.include_router(purchases.router)
app.include_router(commissions.router)
app.include_router(statistics.router)
app.include_router(referrals.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=6410, reload=True)