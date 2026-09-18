"""FastAPI dependencies for ITPlus API."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from itplus.app.core.database import get_db
from itplus.app.core.security import decode_access_token
from itplus.app.models.user import User
from itplus.app.services.rbac import ADMIN_ROLE
from itplus.app.services import session_service
from itplus.app.services.user_service import get_user_by_login

security = HTTPBearer(auto_error=False)


def _token_user(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    return payload


def get_current_token_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    payload = _token_user(credentials)
    jti = payload.get("jti")
    if jti:
        try:
            if not session_service.validate_and_touch(db, jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sesión cerrada por un administrador. Inicia sesión nuevamente.",
                )
        except HTTPException:
            raise
        except Exception:
            pass
    return payload


def get_current_user(
    token_user: dict = Depends(get_current_token_user),
    db: Session = Depends(get_db),
) -> User:
    user = get_user_by_login(db, token_user["username"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario está inactivo. Contacta al administrador.",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.rol_name.lower() != ADMIN_ROLE.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requiere rol de Administrador.",
        )
    return current_user


