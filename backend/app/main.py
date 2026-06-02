from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.ws.manager import manager
from app.core.cv_worker import cv_worker_loop
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static exports
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Routes
app.include_router(auth_router)
app.include_router(upload_router)


# START WORKER (clean modern style)
@app.on_event("startup")
async def startup():
    asyncio.create_task(cv_worker_loop())
    print("CV worker started")


# WebSocket
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    finally:
        manager.disconnect(websocket)