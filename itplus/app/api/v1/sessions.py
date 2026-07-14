"""Session monitoring and revocation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_token_user, require_admin
from itplus.app.core.database import get_db
from itplus.app.models.user import User
from itplus.app.schemas.admin import RevokeSessionRequest
from itplus.app.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def listar(
    token_user: dict = Depends(get_current_token_user),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "sessions": session_service.list_active_sessions(db),
        "current_jti": token_user.get("jti"),
    }


@router.get("/history")
def historial(
    limit: int = 200,
    usuario: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "sessions": session_service.list_session_history(
            db, min(max(limit, 1), 1000), usuario, desde, hasta
        )
    }


@router.post("/revoke")
def revocar(
    body: RevokeSessionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ok, msg = session_service.revoke_session(db, body.jti)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    logger.info("Sesión '%s' revocada por '%s'", body.jti, current_user.username)
    return {"ok": True}
