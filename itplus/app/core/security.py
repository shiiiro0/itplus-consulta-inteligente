"""Password hashing and JWT utilities."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt

from itplus.app.core.config import get_settings

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Hash bcrypt fijo, sin significado real, usado solo para igualar tiempos de
# respuesta en el login cuando el usuario no existe. Sin esto, un login con
# un username inexistente se resolvía casi al instante (nunca se llamaba a
# bcrypt.checkpw), mientras que un username real con contraseña incorrecta
# tardaba lo que tarda bcrypt (decenas de ms) — un canal lateral de tiempo
# que permite enumerar qué usernames existen sin ver ningún mensaje de error
# distinto.
_DUMMY_PASSWORD_HASH = get_password_hash("itplus-dummy-password-for-constant-time-login")


def verify_password_constant_time(plain_password: str, hashed_password: str | None) -> bool:
    """Como verify_password, pero siempre ejecuta bcrypt.checkpw (contra un
    hash dummy si hashed_password es None) para no filtrar por tiempo si el
    usuario existe o no."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        (hashed_password or _DUMMY_PASSWORD_HASH).encode("utf-8"),
    )


def create_access_token(
    subject: str,
    rol: str,
    *,
    jti: str | None = None,
    expire: datetime | None = None,
) -> str:
    settings = get_settings()
    if expire is None:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    payload: dict[str, Any] = {
        "sub": subject,
        "rol": rol,
        "exp": expire,
    }
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    username = payload.get("sub", "")
    if not username:
        raise ValueError("Invalid token")
    return {
        "username": str(username),
        "rol": str(payload.get("rol", "Usuario")),
        "jti": payload.get("jti"),
        "exp": payload.get("exp"),
    }
