"""User administration service."""

from __future__ import annotations

import re
import uuid as uuid_lib

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from itplus.app.core.security import get_password_hash
from itplus.app.models.role import Role
from itplus.app.models.user import User
from itplus.app.services.rbac import ADMIN_ROLE, get_role_by_name

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validar_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def list_users(db: Session) -> list[dict]:
    users = db.scalars(
        select(User).options(joinedload(User.role_obj)).order_by(User.nombre)
    ).all()
    return [
        {
            "id": str(u.id),
            "nombre": u.nombre,
            "username": u.username,
            "correo": u.email,
            "rol": u.rol_name,
            "activo": u.activo,
            "fecha_creacion": u.created_at.isoformat() if u.created_at else None,
            "fecha_actualizacion": None,
        }
        for u in users
    ]


def list_role_names(db: Session) -> list[str]:
    return list(db.scalars(select(Role.role_name).order_by(Role.role_name)).all())


def check_duplicates(
    db: Session,
    username: str,
    email: str,
    exclude_id: str | None = None,
) -> dict[str, bool]:
    email_norm = (email or "").strip().lower()
    username_norm = (username or "").strip()

    q_user = select(User).where(User.username == username_norm)
    q_email = select(User).where(func.lower(User.email) == email_norm)
    if exclude_id:
        uid = uuid_lib.UUID(exclude_id)
        q_user = q_user.where(User.id != uid)
        q_email = q_email.where(User.id != uid)

    return {
        "username": db.scalar(q_user) is not None,
        "email": bool(email_norm) and db.scalar(q_email) is not None,
    }


def count_active_admins(db: Session) -> int:
    admin_role = get_role_by_name(db, ADMIN_ROLE)
    if admin_role is None:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role_id == admin_role.id, User.activo.is_(True))
        )
        or 0
    )


def _resolve_role(db: Session, rol: str) -> Role | None:
    name = (rol or "Usuario").strip()
    role = get_role_by_name(db, name)
    if role is None:
        role = Role(role_name=name)
        db.add(role)
        db.flush()
    return role


def create_user(
    db: Session,
    nombre: str,
    username: str,
    correo: str,
    password_plain: str,
    rol: str,
    activo: bool = True,
) -> tuple[bool, str]:
    role = _resolve_role(db, rol)
    user = User(
        nombre=nombre.strip(),
        username=username.strip(),
        email=correo.strip().lower(),
        password_hash=get_password_hash(password_plain),
        role_id=role.id if role else None,
        role=rol,
        activo=activo,
    )
    db.add(user)
    try:
        db.commit()
        return True, ""
    except Exception as exc:
        db.rollback()
        return False, str(exc)


def update_user(
    db: Session,
    user_id: str,
    nombre: str,
    username: str,
    correo: str,
    rol: str,
    activo: bool,
    password_plain: str | None = None,
) -> tuple[bool, str]:
    user = db.get(User, uuid_lib.UUID(user_id))
    if user is None:
        return False, "Usuario no encontrado."

    role = _resolve_role(db, rol)
    user.nombre = nombre.strip()
    user.username = username.strip()
    user.email = correo.strip().lower()
    user.activo = activo
    user.role_id = role.id if role else None
    user.role = rol
    if password_plain:
        user.password_hash = get_password_hash(password_plain)

    try:
        db.commit()
        return True, ""
    except Exception as exc:
        db.rollback()
        return False, str(exc)


def delete_user(db: Session, user_id: str) -> tuple[bool, str]:
    user = db.get(User, uuid_lib.UUID(user_id))
    if user is None:
        return False, "Usuario no encontrado."
    db.delete(user)
    try:
        db.commit()
        return True, ""
    except Exception as exc:
        db.rollback()
        return False, str(exc)


def get_user_by_login(db: Session, login: str) -> User | None:
    value = (login or "").strip()
    if not value:
        return None
    return db.scalar(
        select(User)
        .options(joinedload(User.role_obj))
        .where(or_(User.username == value, func.lower(User.email) == value.lower()))
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    value = (email or "").strip().lower()
    if not value:
        return None
    return db.scalar(
        select(User)
        .options(joinedload(User.role_obj))
        .where(func.lower(User.email) == value)
    )
