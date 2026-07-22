from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
import asyncio
import os

from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.ws.manager import manager
from app.core.cv_worker import cv_worker_loop
from app.core.auth_schema import init_auth_db
from app.db_mysql import SessionLocal

app = FastAPI(title="Talent Desk API")

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://machine-thieving-rural.ngrok-free.dev",
        "https://talent-desk-inky.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Static Files
# =========================
os.makedirs("exports", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

app.mount("/exports", StaticFiles(directory="exports"), name="exports")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# =========================
# Routes
# =========================
app.include_router(auth_router)
app.include_router(upload_router)

# =========================
# Startup Worker
# =========================
@app.on_event("startup")
async def startup():
    db = SessionLocal()
    try:
        init_auth_db(db)
        print("Auth tables ready")
    finally:
        db.close()

    if os.getenv("ENABLE_CV_WORKER", "true").lower() == "true":
        asyncio.create_task(cv_worker_loop())
        print("CV worker started")


# =========================
# WebSocket
# =========================
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)