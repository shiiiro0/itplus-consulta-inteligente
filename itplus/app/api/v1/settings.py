"""Editable security settings."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import require_admin
from itplus.app.core.database import get_db
from itplus.app.models.user import User
from itplus.app.schemas.admin import SettingsUpdate
from itplus.app.services import settings_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def listar(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"settings": settings_service.get_all(db)}


@router.put("/")
def actualizar(
    body: SettingsUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not body.values:
        raise HTTPException(status_code=400, detail="Sin valores para actualizar.")
    ok, msg = settings_service.set_many(db, body.values, current_user.username)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    logger.info("Configuración actualizada por '%s'", current_user.username)
    return {"ok": True, "settings": settings_service.get_all(db)}
