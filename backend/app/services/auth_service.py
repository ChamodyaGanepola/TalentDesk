import os

import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str):
    return db.execute(
        text("""
            SELECT id, name, email, password_hash, is_active
            FROM users
            WHERE email = :email
            LIMIT 1
        """),
        {"email": _normalize_email(email)},
    ).mappings().first()


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False
