"""User administration endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user, require_admin
from itplus.app.core.database import get_db
from itplus.app.models.user import User
from itplus.app.schemas.users import UsuarioCreate, UsuarioUpdate, UsuariosListResponse
from itplus.app.services.rbac import ADMIN_ROLE
from itplus.app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=UsuariosListResponse)
def listar_usuarios(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = user_service.list_users(db)
    return UsuariosListResponse(data=data, total=len(data))


@router.get("/roles")
def listar_roles(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"roles": user_service.list_role_names(db)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_usuario(
    body: UsuarioCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not user_service.validar_email(body.correo):
        raise HTTPException(status_code=400, detail="El correo no tiene un formato válido.")

    dup = user_service.check_duplicates(db, body.username, str(body.correo))
    if dup["username"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El username '{body.username}' ya está registrado.",
        )
    if dup["email"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El correo '{body.correo}' ya está registrado.",
        )

    ok, msg = user_service.create_user(
        db,
        nombre=body.nombre,
        username=body.username,
        correo=str(body.correo),
        password_plain=body.password,
        rol=body.rol,
        activo=body.activo,
    )
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {msg}")

    logger.info("Usuario '%s' creado por '%s'", body.username, current_user.username)
    return {"ok": True, "username": body.username}


@router.put("/{user_id}")
def actualizar_usuario(
    user_id: uuid.UUID,
    body: UsuarioUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    dup = user_service.check_duplicates(
        db, body.username, str(body.correo), exclude_id=str(user_id)
    )
    if dup["username"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El username '{body.username}' ya está en uso.",
        )
    if dup["email"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El correo '{body.correo}' ya está en uso.",
        )

    if target.rol_name == ADMIN_ROLE and (body.rol != ADMIN_ROLE or not body.activo):
        if user_service.count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No puedes cambiar el rol o inactivar al único administrador activo.",
            )

    ok, msg = user_service.update_user(
        db,
        user_id=str(user_id),
        nombre=body.nombre,
        username=body.username,
        correo=str(body.correo),
        rol=body.rol,
        activo=body.activo,
        password_plain=body.password,
    )
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al actualizar usuario: {msg}")

    logger.info("Usuario %s actualizado por '%s'", user_id, current_user.username)
    return {"ok": True}


@router.delete("/{user_id}")
def eliminar_usuario(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if target.rol_name == ADMIN_ROLE and user_service.count_active_admins(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No puedes eliminar al único administrador activo.",
        )

    ok, msg = user_service.delete_user(db, str(user_id))
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al eliminar usuario: {msg}")

    logger.info("Usuario %s eliminado por '%s'", user_id, current_user.username)
    return {"ok": True}
