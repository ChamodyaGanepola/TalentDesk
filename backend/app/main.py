from fastapi import FastAPI, WebSocket
from app.ws.manager import manager
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# normal routes
from app.routes import upload, auth

app.include_router(upload.router)
app.include_router(auth.router)


# 🔌 WEBSOCKET ROUTE (REAL TIME DASHBOARD)
@app.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except:
        manager.disconnect(websocket)


@app.get("/")
def home():
    return {"message": "Backend running"}