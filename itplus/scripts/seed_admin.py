"""Seed default admin user for ITPlus."""

import logging
import os
import sys

from sqlalchemy import select

from itplus.app.core.database import SessionLocal, init_db
from itplus.app.core.security import get_password_hash
from itplus.app.models.user import User
from itplus.app.services.rbac import ADMIN_ROLE, get_role_by_name

logger = logging.getLogger(__name__)

_DEFAULT_EMAIL = "admin@itplus.cl"
_DEFAULT_PASSWORD = "admin123"


def seed_admin(
    email: str | None = None,
    password: str | None = None,
    username: str = "admin",
    nombre: str = "Administrador ITPlus",
) -> None:
    # Prioridad: argumento explícito > variable de entorno > valor por
    # defecto documentado. Así se puede fijar ADMIN_EMAIL/ADMIN_PASSWORD en
    # el .env sin tocar código, y en producción es responsabilidad de quien
    # despliega definirlas.
    email = email or os.environ.get("ADMIN_EMAIL", _DEFAULT_EMAIL)
    password = password or os.environ.get("ADMIN_PASSWORD", _DEFAULT_PASSWORD)

    if email == _DEFAULT_EMAIL and password == _DEFAULT_PASSWORD:
        logger.warning(
            "Sembrando el usuario admin con las credenciales POR DEFECTO "
            "(%s / %s). Esto es aceptable solo para desarrollo local. "
            "Define ADMIN_EMAIL y ADMIN_PASSWORD en tu .env antes de "
            "desplegar en producción, o cambia la contraseña desde la UI "
            "apenas inicies sesión.",
            _DEFAULT_EMAIL,
            _DEFAULT_PASSWORD,
        )

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
    logging.basicConfig(level=logging.INFO)
    cli_email = sys.argv[1] if len(sys.argv) > 1 else None
    cli_password = sys.argv[2] if len(sys.argv) > 2 else None
    seed_admin(cli_email, cli_password)
