"""Seed default admin user for ITPlus."""

import sys

from sqlalchemy import select

from itplus.app.core.database import SessionLocal, init_db
from itplus.app.core.security import get_password_hash
from itplus.app.models.user import User
from itplus.app.services.rbac import ADMIN_ROLE, get_role_by_name


def seed_admin(
    email: str = "admin@itplus.cl",
    password: str = "admin123",
    username: str = "admin",
    nombre: str = "Administrador ITPlus",
) -> None:
    init_db()
    db = SessionLocal()
    try:
        admin_role = get_role_by_name(db, ADMIN_ROLE)
        existing = db.scalar(
            select(User).where((User.email == email) | (User.username == username))
        )
        if existing:
            changed = False
            if admin_role and existing.role_id != admin_role.id:
                existing.role_id = admin_role.id
                existing.role = ADMIN_ROLE
                changed = True
            if not existing.username:
                existing.username = username
                changed = True
            if not existing.nombre:
                existing.nombre = nombre
                changed = True
            if changed:
                db.commit()
                print(f"Updated admin user: {email}")
            else:
                print(f"User {email} already exists")
            return

        user = User(
            username=username,
            email=email,
            nombre=nombre,
            password_hash=get_password_hash(password),
            role=ADMIN_ROLE,
            role_id=admin_role.id if admin_role else None,
            activo=True,
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
