from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.ws.manager import manager
from app.core.cv_worker import cv_worker_loop

app = FastAPI()

# ======================
# CORS
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# ROUTES
# ======================
app.include_router(auth_router)
app.include_router(upload_router)


# ======================
# START WORKER AUTOMATICALLY
# ======================
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cv_worker_loop())
    print("🔥 Background CV worker started")


# ======================
# WEBSOCKET
# ======================
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):

    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)