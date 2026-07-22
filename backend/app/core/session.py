import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db_mysql import SessionLocal

ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "30"))
REFRESH_TOKEN_TTL_HOURS = int(os.getenv("REFRESH_TOKEN_TTL_HOURS", "168"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user_from_row(row) -> dict[str, str]:
    return {
        "id": str(row["user_id"]),
        "name": row["name"],
        "email": row["email"],
    }


class SessionStore:
    def create_pair(self, user_id: int, user: dict[str, str]) -> dict[str, str]:
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(48)
        expires_at = _utcnow() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
        refresh_expires_at = _utcnow() + timedelta(hours=REFRESH_TOKEN_TTL_HOURS)

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO sessions (
                        user_id, token, refresh_token, expires_at, refresh_expires_at
                    )
                    VALUES (
                        :user_id, :token, :refresh_token, :expires_at, :refresh_expires_at
                    )
                """),
                {
                    "user_id": user_id,
                    "token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "refresh_expires_at": refresh_expires_at,
                },
            )
            db.commit()
        finally:
            db.close()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def get(self, access_token: str) -> dict[str, str] | None:
        if not access_token:
            return None

        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT s.user_id, u.name, u.email, s.expires_at, s.revoked_at
                    FROM sessions s
                    JOIN users u ON u.id = s.user_id
                    WHERE s.token = :token
                    LIMIT 1
                """),
                {"token": access_token},
            ).mappings().first()

            if not row or row["revoked_at"] is not None:
                return None

            if row["expires_at"] <= _utcnow():
                return None

            return _user_from_row(row)
        finally:
            db.close()

    def refresh(self, refresh_token: str) -> dict[str, str] | None:
        if not refresh_token:
            return None

        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT s.id, s.user_id, u.name, u.email,
                           s.revoked_at, s.refresh_expires_at
                    FROM sessions s
                    JOIN users u ON u.id = s.user_id
                    WHERE s.refresh_token = :refresh_token
                    LIMIT 1
                """),
                {"refresh_token": refresh_token},
            ).mappings().first()

            if not row or row["revoked_at"] is not None:
                return None

            if not row["refresh_expires_at"] or row["refresh_expires_at"] <= _utcnow():
                db.execute(
                    text("UPDATE sessions SET revoked_at = :revoked_at WHERE id = :id"),
                    {"revoked_at": _utcnow(), "id": row["id"]},
                )
                db.commit()
                return None

            new_access = secrets.token_urlsafe(32)
            new_refresh = secrets.token_urlsafe(48)
            expires_at = _utcnow() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
            refresh_expires_at = _utcnow() + timedelta(hours=REFRESH_TOKEN_TTL_HOURS)

            db.execute(
                text("""
                    UPDATE sessions
                    SET token = :token,
                        refresh_token = :refresh_token,
                        expires_at = :expires_at,
                        refresh_expires_at = :refresh_expires_at
                    WHERE id = :id
                """),
                {
                    "token": new_access,
                    "refresh_token": new_refresh,
                    "expires_at": expires_at,
                    "refresh_expires_at": refresh_expires_at,
                    "id": row["id"],
                },
            )
            db.commit()

            return {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "user": _user_from_row(row),
            }
        finally:
            db.close()

    def revoke(self, access_token: str) -> None:
        if not access_token:
            return

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE sessions
                    SET revoked_at = :revoked_at
                    WHERE token = :token AND revoked_at IS NULL
                """),
                {"token": access_token, "revoked_at": _utcnow()},
            )
            db.commit()
        finally:
            db.close()

    def revoke_by_refresh(self, refresh_token: str) -> None:
        if not refresh_token:
            return

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE sessions
                    SET revoked_at = :revoked_at
                    WHERE refresh_token = :refresh_token AND revoked_at IS NULL
                """),
                {"refresh_token": refresh_token, "revoked_at": _utcnow()},
            )
            db.commit()
        finally:
            db.close()


sessions = SessionStore()
