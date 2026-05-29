from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.ws.manager import manager

app = FastAPI()

# ======================================
# CORS
# ======================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================
# ROUTERS
# ======================================
app.include_router(auth_router)
app.include_router(upload_router)


# ======================================
# WEBSOCKET
# ======================================
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):

    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)