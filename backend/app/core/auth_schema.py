import os

import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "chamodyaagra2000@gmail.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345678")
DEFAULT_ADMIN_NAME = os.getenv("ADMIN_NAME", "Chamodya")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
        """),
        {"table_name": table, "column_name": column},
    ).fetchone()
    return row is not None


def _table_exists(db: Session, table: str) -> bool:
    row = db.execute(
        text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
            LIMIT 1
        """),
        {"table_name": table},
    ).fetchone()
    return row is not None


def _ensure_index(db: Session, table: str, index_name: str, columns: str) -> None:
    exists = db.execute(
        text("""
            SELECT 1
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND index_name = :index_name
            LIMIT 1
        """),
        {"table_name": table, "index_name": index_name},
    ).fetchone()

    if not exists:
        db.execute(text(f"CREATE INDEX {index_name} ON {table} ({columns})"))


def _drop_column_if_exists(db: Session, table: str, column: str) -> None:
    if _column_exists(db, table, column):
        db.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))


def ensure_auth_tables(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sessions (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            token VARCHAR(128) NOT NULL UNIQUE,
            refresh_token VARCHAR(128) NULL UNIQUE,
            expires_at DATETIME(6) NOT NULL,
            refresh_expires_at DATETIME(6) NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            revoked_at DATETIME(6) NULL,
            CONSTRAINT fk_sessions_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """))

    # Migrate legacy sessions schema (email/name columns, missing user_id)
    if _table_exists(db, "sessions"):
        if not _column_exists(db, "sessions", "user_id"):
            db.execute(text("ALTER TABLE sessions ADD COLUMN user_id INT NULL"))

        if _column_exists(db, "sessions", "email"):
            db.execute(text("""
                UPDATE sessions s
                JOIN users u ON LOWER(u.email) = LOWER(s.email)
                SET s.user_id = u.id
                WHERE s.user_id IS NULL
            """))

        db.execute(text("DELETE FROM sessions WHERE user_id IS NULL"))

        if _column_exists(db, "sessions", "user_id"):
            db.execute(text("ALTER TABLE sessions MODIFY COLUMN user_id INT NOT NULL"))

        _drop_column_if_exists(db, "sessions", "email")
        _drop_column_if_exists(db, "sessions", "name")

    if _table_exists(db, "login_otps"):
        db.execute(text("DROP TABLE login_otps"))

    _ensure_index(db, "sessions", "idx_sessions_token", "token")
    _ensure_index(db, "sessions", "idx_sessions_refresh", "refresh_token")
    _ensure_index(db, "sessions", "idx_sessions_user", "user_id")
    _ensure_index(db, "sessions", "idx_sessions_expires", "expires_at")

    db.commit()


def seed_default_admin(db: Session) -> None:
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email LIMIT 1"),
        {"email": DEFAULT_ADMIN_EMAIL.lower()},
    ).fetchone()

    password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)

    if existing:
        db.execute(
            text("""
                UPDATE users
                SET name = :name,
                    password_hash = :password_hash,
                    is_active = 1
                WHERE email = :email
            """),
            {
                "name": DEFAULT_ADMIN_NAME,
                "password_hash": password_hash,
                "email": DEFAULT_ADMIN_EMAIL.lower(),
            },
        )
    else:
        db.execute(
            text("""
                INSERT INTO users (name, email, password_hash, is_active)
                VALUES (:name, :email, :password_hash, 1)
            """),
            {
                "name": DEFAULT_ADMIN_NAME,
                "password_hash": password_hash,
                "email": DEFAULT_ADMIN_EMAIL.lower(),
            },
        )

    db.commit()


def init_auth_db(db: Session) -> None:
    ensure_auth_tables(db)
    seed_default_admin(db)
