from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.session import sessions
from app.db_mysql import get_db
from app.services.auth_service import get_user_by_email, verify_password

router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)

    if not user or not user["is_active"]:
        return {"success": False, "message": "Invalid credentials"}

    if not verify_password(data.password, user["password_hash"]):
        return {"success": False, "message": "Invalid credentials"}

    profile = {"name": user["name"], "email": user["email"]}
    tokens = sessions.create_pair(user["id"], profile)

    return {
        "success": True,
        "message": "Login successful",
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token": tokens["access_token"],
        "user": profile,
    }


@router.post("/refresh")
def refresh_tokens(data: RefreshRequest):
    result = sessions.refresh(data.refresh_token)

    if not result:
        return {
            "success": False,
            "message": "Invalid or expired refresh token",
        }

    return {
        "success": True,
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token": result["access_token"],
        "user": result["user"],
    }


@router.get("/me")
def me(user: dict[str, str] = Depends(get_current_user)):
    return {"success": True, "user": user}


@router.post("/logout")
def logout(
    body: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    _user: dict[str, str] = Depends(get_current_user),
):
    if credentials:
        sessions.revoke(credentials.credentials)

    if body and body.refresh_token:
        sessions.revoke_by_refresh(body.refresh_token)

    return {"success": True, "message": "Logged out"}
