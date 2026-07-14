"""Role and permission endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import require_admin
from itplus.app.core.database import get_db
from itplus.app.models.user import User
from itplus.app.schemas.roles import RolCreate, RolesListResponse, RolUpdate, RolItem, SistemaItem
from itplus.app.services import rbac

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=RolesListResponse)
def listar(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    roles = [RolItem(**item) for item in rbac.list_roles_with_permissions(db)]
    sistemas = [SistemaItem(**item) for item in rbac.list_modules(db)]
    return RolesListResponse(roles=roles, sistemas=sistemas)


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear(
    body: RolCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok, msg = rbac.create_role(db, body.role_name, body.sistemas)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    logger.info("Rol '%s' creado por '%s'", body.role_name, current_user.username)
    return {"ok": True}


@router.put("/{role_id}")
def actualizar(
    role_id: int,
    body: RolUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok, msg = rbac.update_role(db, role_id, body.role_name, body.sistemas)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    logger.info("Rol ID=%s actualizado por '%s'", role_id, current_user.username)
    return {"ok": True}


@router.delete("/{role_id}")
def eliminar(
    role_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok, msg = rbac.delete_role(db, role_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    logger.info("Rol ID=%s eliminado por '%s'", role_id, current_user.username)
    return {"ok": True}
