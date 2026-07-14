"""Auth endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user, require_admin
from itplus.app.core.azure_auth import AzureAuthError, is_azure_configured, validar_token_azure
from itplus.app.core.database import get_db
from itplus.app.core.security import create_access_token, verify_password
from itplus.app.models.user import User
from itplus.app.schemas.auth import (
    AzureLoginRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    UserResponse,
)
from itplus.app.services import session_service, settings_service
from itplus.app.services.rbac import get_permisos_for_role
from itplus.app.services.user_service import get_user_by_email, get_user_by_login

logger = logging.getLogger(__name__)

router = APIRouter()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def _token_expire(db: Session) -> datetime:
    hours = settings_service.get_int(db, "token_expire_hours")
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def _register_session(
    db: Session,
    jti: str,
    username: str,
    method: str,
    expire: datetime,
    request: Request,
) -> None:
    ua = request.headers.get("user-agent", "")
    ip = _client_ip(request)
    device_id = request.headers.get("x-device-id", "")
    session_service.create_session(db, jti, username, method, expire, ip, ua, device_id)
    session_service.revoke_user_device_sessions(
        db, username, ip, ua, except_jti=jti, device_id=device_id
    )


def _build_login_response(db: Session, user: User, token: str) -> LoginResponse:
    return LoginResponse(
        access_token=token,
        username=user.username,
        email=user.email,
        rol=user.rol_name,
        permisos=get_permisos_for_role(db, user.rol_name),
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = get_user_by_login(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario está inactivo. Contacta al administrador.",
        )

    jti = uuid.uuid4().hex
    expire = _token_expire(db)
    token = create_access_token(user.username, user.rol_name, jti=jti, expire=expire)
    _register_session(db, jti, user.username, "local", expire, request)
    logger.info("Login exitoso para '%s' (rol: %s)", user.username, user.rol_name)
    return _build_login_response(db, user, token)


@router.post("/azure", response_model=LoginResponse)
def login_azure(payload: AzureLoginRequest, request: Request, db: Session = Depends(get_db)):
    if not is_azure_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El inicio de sesión con Microsoft no está habilitado en este entorno.",
        )

    try:
        info = validar_token_azure(payload.token)
    except AzureAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = get_user_by_email(db, info["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tu cuenta de Microsoft no está habilitada en el sistema. "
                "Solicita al administrador que registre tu correo."
            ),
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario está inactivo. Contacta al administrador.",
        )

    jti = uuid.uuid4().hex
    expire = _token_expire(db)
    token = create_access_token(user.username, user.rol_name, jti=jti, expire=expire)
    _register_session(db, jti, user.username, "azure", expire, request)
    logger.info("Login Azure exitoso para '%s' (%s)", user.username, info["email"])
    return _build_login_response(db, user, token)


@router.get("/azure/status")
def azure_status():
    return {"enabled": is_azure_configured()}


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeResponse(
        username=current_user.username,
        email=current_user.email,
        nombre=current_user.nombre,
        rol=current_user.rol_name,
        permisos=get_permisos_for_role(db, current_user.rol_name),
    )


@router.get("/profile", response_model=UserResponse)
def profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nombre=current_user.nombre,
        rol=current_user.rol_name,
        activo=current_user.activo,
        created_at=current_user.created_at,
    )
