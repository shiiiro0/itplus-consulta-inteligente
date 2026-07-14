"""RBAC: module catalog, role permissions, startup seed."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from itplus.app.models.role import Role, SystemModule
from itplus.app.models.user import User

logger = logging.getLogger(__name__)

ADMIN_ROLE = "Administrador"

MODULE_CATALOG: list[tuple[str, str]] = [
    ("dashboard", "Inicio"),
    ("asistente", "Asistente Gerencial"),
    ("bot", "ITPlusBot"),
    ("consulta", "Consulta RAG"),
    ("documentos", "Documentos"),
    ("historial", "Historial"),
]

MODULE_KEYS = [key for key, _ in MODULE_CATALOG]

ADMIN_ONLY_MODULES = ["usuarios", "roles", "sesiones"]

DEFAULT_USER_MODULES = ["dashboard", "asistente", "bot", "consulta", "historial"]
DEFAULT_EDITOR_MODULES = ["dashboard", "asistente", "bot", "consulta", "documentos", "historial"]
DEFAULT_CONSULTA_MODULES = ["dashboard", "asistente", "consulta"]

BASE_ROLES: dict[str, list[str]] = {
    ADMIN_ROLE: MODULE_KEYS + ADMIN_ONLY_MODULES,
    "Usuario": DEFAULT_USER_MODULES,
    "Editor": DEFAULT_EDITOR_MODULES,
    "Consultas": DEFAULT_CONSULTA_MODULES,
}


def _default_modules_for(role_name: str) -> list[str]:
    key = (role_name or "").strip()
    if key in BASE_ROLES:
        return list(BASE_ROLES[key])
    lowered = key.lower()
    if lowered == "administrador":
        return list(BASE_ROLES[ADMIN_ROLE])
    if lowered == "consultas":
        return list(DEFAULT_CONSULTA_MODULES)
    return list(DEFAULT_USER_MODULES)


def seed_rbac(db: Session) -> None:
    """Idempotent seed of modules and base roles."""
    all_module_defs = MODULE_CATALOG + [
        ("usuarios", "Administración de Usuarios"),
        ("roles", "Roles y Permisos"),
        ("sesiones", "Sesiones y Seguridad"),
    ]
    for key, label in all_module_defs:
        mod = db.scalar(select(SystemModule).where(SystemModule.key == key))
        if mod is None:
            db.add(SystemModule(key=key, label=label))

    db.flush()

    all_modules = {
        m.key: m for m in db.scalars(select(SystemModule)).all()
    }

    _ensure_module_on_roles(db, all_modules, "asistente", ["Administrador", "Usuario", "Editor", "Consultas"])

    for role_name, module_keys in BASE_ROLES.items():
        role = db.scalar(select(Role).where(Role.role_name == role_name))
        if role is None:
            role = Role(role_name=role_name)
            db.add(role)
            db.flush()
            role.modules = [all_modules[k] for k in module_keys if k in all_modules]
        elif not role.modules:
            role.modules = [all_modules[k] for k in module_keys if k in all_modules]

    db.commit()
    migrate_legacy_users(db)


def _ensure_module_on_roles(
    db: Session,
    all_modules: dict,
    module_key: str,
    role_names: list[str],
) -> None:
    """Attach a new module to existing roles (idempotent)."""
    mod = all_modules.get(module_key)
    if mod is None:
        return
    for role_name in role_names:
        role = db.scalar(select(Role).where(Role.role_name == role_name))
        if role is None:
            continue
        existing = {m.key for m in role.modules}
        if module_key not in existing:
            role.modules = list(role.modules) + [mod]
    db.flush()


def migrate_legacy_users(db: Session) -> None:
    """Backfill username/role_id for users created before RBAC."""
    users = db.scalars(select(User)).all()
    admin_role = db.scalar(select(Role).where(Role.role_name == ADMIN_ROLE))
    user_role = db.scalar(select(Role).where(Role.role_name == "Usuario"))

    for user in users:
        if not user.username:
            base = user.email.split("@")[0] if user.email else "user"
            candidate = base
            n = 1
            while db.scalar(select(User).where(User.username == candidate, User.id != user.id)):
                candidate = f"{base}{n}"
                n += 1
            user.username = candidate

        if not user.nombre:
            user.nombre = user.username

        if user.role_id is None:
            legacy = (user.role or "").strip().lower()
            if legacy in ("admin", "administrador") and admin_role:
                user.role_id = admin_role.id
            elif user_role:
                user.role_id = user_role.id

    db.commit()


def get_permisos_for_role(db: Session, role_name: str) -> list[str]:
    if (role_name or "").strip().lower() == ADMIN_ROLE.lower():
        return MODULE_KEYS + ADMIN_ONLY_MODULES

    role = db.scalar(select(Role).where(Role.role_name == role_name))
    if role is None:
        return list(DEFAULT_USER_MODULES)

    return sorted({m.key for m in role.modules})


def list_modules(db: Session) -> list[dict[str, str]]:
    modules = db.scalars(
        select(SystemModule).where(SystemModule.key.notin_(ADMIN_ONLY_MODULES)).order_by(SystemModule.key)
    ).all()
    admin_modules = db.scalars(
        select(SystemModule).where(SystemModule.key.in_(ADMIN_ONLY_MODULES)).order_by(SystemModule.key)
    ).all()
    return [{"clave": m.key, "label": m.label} for m in list(modules) + list(admin_modules)]


def list_roles_with_permissions(db: Session) -> list[dict]:
    roles = db.scalars(select(Role).order_by(Role.role_name)).all()
    out: list[dict] = []
    for role in roles:
        user_count = db.scalar(
            select(func.count()).select_from(User).where(User.role_id == role.id)
        )
        out.append(
            {
                "role_id": role.id,
                "role_name": role.role_name,
                "es_admin": role.role_name.lower() == ADMIN_ROLE.lower(),
                "usuarios": int(user_count or 0),
                "sistemas": sorted(m.key for m in role.modules),
            }
        )
    return out


def create_role(db: Session, role_name: str, sistemas: list[str]) -> tuple[bool, str]:
    name = (role_name or "").strip()
    if not name:
        return False, "El nombre del rol es obligatorio."
    if name.lower() == ADMIN_ROLE.lower():
        return False, "No se puede crear otro rol llamado Administrador."

    existing = db.scalar(select(Role).where(Role.role_name == name))
    if existing:
        return False, f"El rol '{name}' ya existe."

    allowed = set(MODULE_KEYS)
    keys = [k for k in sistemas if k in allowed]
    modules = list(
        db.scalars(select(SystemModule).where(SystemModule.key.in_(keys))).all()
    ) if keys else []

    role = Role(role_name=name, modules=modules)
    db.add(role)
    db.commit()
    return True, ""


def update_role(
    db: Session, role_id: int, role_name: str, sistemas: list[str]
) -> tuple[bool, str]:
    role = db.get(Role, role_id)
    if role is None:
        return False, "Rol no encontrado."

    if role.role_name.lower() == ADMIN_ROLE.lower():
        return False, "El rol Administrador no se puede modificar."

    name = (role_name or "").strip()
    if not name:
        return False, "El nombre del rol es obligatorio."

    other = db.scalar(select(Role).where(Role.role_name == name, Role.id != role_id))
    if other:
        return False, f"Ya existe otro rol llamado '{name}'."

    allowed = set(MODULE_KEYS)
    keys = [k for k in sistemas if k in allowed]
    role.role_name = name
    role.modules = list(
        db.scalars(select(SystemModule).where(SystemModule.key.in_(keys))).all()
    ) if keys else []
    db.commit()
    return True, ""


def delete_role(db: Session, role_id: int) -> tuple[bool, str]:
    role = db.get(Role, role_id)
    if role is None:
        return False, "Rol no encontrado."

    if role.role_name.lower() == ADMIN_ROLE.lower():
        return False, "No se puede eliminar el rol Administrador."

    if role.role_name.lower() in ("usuario", "consultas", "editor"):
        return False, f"No se puede eliminar el rol base '{role.role_name}'."

    user_count = db.scalar(
        select(func.count()).select_from(User).where(User.role_id == role.id)
    )
    if user_count and user_count > 0:
        return False, "No se puede eliminar un rol con usuarios asignados."

    db.delete(role)
    db.commit()
    return True, ""


def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.role_name == role_name))
