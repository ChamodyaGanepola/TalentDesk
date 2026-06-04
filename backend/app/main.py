from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
import asyncio

from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.ws.manager import manager
from app.core.cv_worker import cv_worker_loop

app = FastAPI()

# =========================
# CORS CONFIG (FIXED)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://talent-desk-inky.vercel.app/",
    ],
    allow_credentials=False,  # must be False when using "*" or wildcard patterns
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# STATIC FILES
# =========================
app.mount("/exports", StaticFiles(directory="exports"), name="exports")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

# =========================
# ROUTES
# =========================
app.include_router(auth_router)
app.include_router(upload_router)

# =========================
# STARTUP WORKER
# =========================
@app.on_event("startup")
async def startup():
    asyncio.create_task(cv_worker_loop())
    print("CV worker started")

# =========================
# WEBSOCKET
# =========================
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)