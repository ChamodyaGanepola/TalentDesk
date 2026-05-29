from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

class LoginRequest(BaseModel):
    email: str
    password: str

ADMIN = {
    "email": "admin@gmail.com",
    "password": "123456",
    "name": "Admin"
}

@router.post("/login")
def login(data: LoginRequest):
    if data.email == ADMIN["email"] and data.password == ADMIN["password"]:
        return {
            "success": True,
            "message": "Login successful",
            "user": {
                "name": ADMIN["name"],
                "email": ADMIN["email"]
            }
        }

    return {
        "success": False,
        "message": "Invalid credentials"
    }