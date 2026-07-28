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
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
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

        from app.routes.upload import (
            ensure_batch_user_isolation,
            ensure_failure_reason_column,
            ensure_include_internships_column,
            ensure_profession_schema,
        )

        ensure_include_internships_column(db)
        ensure_profession_schema(db)
        ensure_failure_reason_column(db)
        ensure_batch_user_isolation(db)
        print("Profession / internship / failure-reason / user-isolation schema ready")
    finally:
        db.close()

    if os.getenv("ENABLE_CV_WORKER", "true").lower() == "true":
        asyncio.create_task(cv_worker_loop())
        print("CV worker started")

    from app.services.export_service import format_experience_for_excel

    print(
        "Excel experience format:",
        format_experience_for_excel(38),
    )


# =========================
# WebSocket
# =========================
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            # Keep the socket open even when the client only listens.
            # A periodic timeout prevents the handler from looking "stuck"
            # and lets broadcasts continue reliably.
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"event": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)