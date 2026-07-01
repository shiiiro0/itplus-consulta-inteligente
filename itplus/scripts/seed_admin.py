"""Seed default admin user for ITPlus."""

import sys

from itplus.app.core.database import SessionLocal, init_db
from itplus.app.core.security import get_password_hash
from itplus.app.models.user import User


def seed_admin(email: str = "admin@itplus.cl", password: str = "admin123") -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists")
            return

        user = User(
            email=email,
            password_hash=get_password_hash(password),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Created admin user: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@itplus.cl"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    seed_admin(email, password)
