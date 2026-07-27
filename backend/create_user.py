"""Create a TalentDesk user with a bcrypt password hash (for MySQL Workbench users).

Usage:
  python create_user.py name email password
"""
import sys

from app.core.auth_schema import hash_password
from app.db_mysql import SessionLocal
from sqlalchemy import text


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: python create_user.py \"Full Name\" email@example.com password")
        sys.exit(1)

    name, email, password = sys.argv[1], sys.argv[2].strip().lower(), sys.argv[3]
    if len(password) < 6:
        print("Password must be at least 6 characters")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.execute(
            text("SELECT id FROM users WHERE email = :email LIMIT 1"),
            {"email": email},
        ).scalar()
        if existing:
            db.execute(
                text(
                    """
                    UPDATE users
                    SET name = :name, password_hash = :password_hash, is_active = 1
                    WHERE email = :email
                    """
                ),
                {
                    "name": name.strip(),
                    "password_hash": hash_password(password),
                    "email": email,
                },
            )
            db.commit()
            print(f"Updated user id={existing} email={email}")
        else:
            db.execute(
                text(
                    """
                    INSERT INTO users (name, email, password_hash, is_active)
                    VALUES (:name, :email, :password_hash, 1)
                    """
                ),
                {
                    "name": name.strip(),
                    "email": email,
                    "password_hash": hash_password(password),
                },
            )
            db.commit()
            new_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            print(f"Created user id={new_id} email={email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
