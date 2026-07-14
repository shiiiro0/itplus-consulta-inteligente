"""Session monitoring and revocation."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from itplus.app.models.user_session import UserSession
from itplus.app.services import settings_service

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_touch: dict[str, float] = {}
_revoked_cache: dict[str, tuple[bool, float]] = {}

_TOUCH_INTERVAL = 60.0
_REVOKED_TTL = 60.0


def create_session(
    db: Session,
    jti: str,
    username: str,
    login_method: str,
    expires_at: datetime | None,
    ip: str | None,
    user_agent: str | None,
    device_id: str | None = None,
) -> None:
    try:
        session = UserSession(
            jti=jti,
            username=username,
            login_method=(login_method or "local")[:10],
            expires_at=expires_at,
            last_seen_at=datetime.now(timezone.utc),
            ip=(ip or "")[:64] or None,
            user_agent=(user_agent or "")[:400] or None,
            device_id=(device_id or "")[:64] or None,
            revoked=False,
        )
        db.add(session)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("No se pudo registrar la sesión '%s': %s", jti, exc)


def touch_session(db: Session, jti: str) -> None:
    now = time.time()
    with _lock:
        if now - _last_touch.get(jti, 0.0) < _TOUCH_INTERVAL:
            return
        _last_touch[jti] = now
    try:
        db.execute(
            update(UserSession)
            .where(UserSession.jti == jti, UserSession.revoked.is_(False))
            .values(last_seen_at=datetime.now(timezone.utc))
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.debug("No se pudo actualizar last_seen de '%s': %s", jti, exc)


def revoke_user_device_sessions(
    db: Session,
    username: str,
    ip: str | None,
    user_agent: str | None,
    except_jti: str,
    device_id: str | None = None,
) -> int:
    try:
        now = datetime.now(timezone.utc)
        dev = (device_id or "").strip()[:64]
        q = select(UserSession).where(
            UserSession.username == username,
            UserSession.revoked.is_(False),
            UserSession.jti != except_jti,
        )
        sessions = db.scalars(q).all()
        count = 0
        for s in sessions:
            if dev:
                if s.device_id == dev:
                    s.revoked = True
                    s.revoked_at = now
                    count += 1
            elif (
                (s.ip or "") == (ip or "")[:64]
                and (s.user_agent or "") == (user_agent or "")[:400]
                and not s.device_id
            ):
                s.revoked = True
                s.revoked_at = now
                count += 1
        db.commit()
        return count
    except Exception as exc:
        db.rollback()
        logger.warning("No se pudieron cerrar sesiones previas de '%s': %s", username, exc)
        return 0


def revoke_session(db: Session, jti: str) -> tuple[bool, str]:
    try:
        session = db.get(UserSession, jti)
        if session is None:
            return False, "Sesión no encontrada."
        session.revoked = True
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
        with _lock:
            _revoked_cache[jti] = (True, time.time())
        return True, ""
    except Exception as exc:
        db.rollback()
        return False, str(exc)


def is_revoked(db: Session, jti: str) -> bool:
    now = time.time()
    with _lock:
        cached = _revoked_cache.get(jti)
        if cached and (now - cached[1]) < _REVOKED_TTL:
            return cached[0]

    revoked = False
    try:
        session = db.get(UserSession, jti)
        if session is not None:
            revoked = bool(session.revoked)
    except Exception as exc:
        logger.debug("No se pudo verificar revocación de '%s': %s", jti, exc)

    with _lock:
        _revoked_cache[jti] = (revoked, now)
    return revoked


def validate_and_touch(db: Session, jti: str) -> bool:
    if is_revoked(db, jti):
        return False
    touch_session(db, jti)
    return True


def list_active_sessions(db: Session) -> list[dict]:
    idle = settings_service.get_int(db, "session_idle_minutes")
    now = datetime.now(timezone.utc)
    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.revoked.is_(False))
        .order_by(UserSession.username, UserSession.last_seen_at.desc())
    ).all()

    out: list[dict] = []
    for s in sessions:
        if s.expires_at and s.expires_at <= now:
            continue
        if idle > 0 and s.last_seen_at:
            if s.last_seen_at < now - timedelta(minutes=idle):
                continue
        out.append(_session_to_dict(s))
    return out


def list_session_history(
    db: Session,
    limit: int = 200,
    usuario: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> list[dict]:
    q = select(UserSession).order_by(UserSession.created_at.desc()).limit(min(max(limit, 1), 1000))
    if usuario:
        q = q.where(UserSession.username.ilike(f"%{usuario.strip()}%"))
    if desde:
        q = q.where(UserSession.created_at >= datetime.fromisoformat(desde))
    if hasta:
        end = datetime.fromisoformat(hasta) + timedelta(days=1)
        q = q.where(UserSession.created_at < end)

    return [_session_to_dict(s) for s in db.scalars(q).all()]


def purge_old_sessions(db: Session, months: int) -> int:
    if months <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    try:
        sessions = db.scalars(
            select(UserSession).where(UserSession.created_at < cutoff)
        ).all()
        for s in sessions:
            db.delete(s)
        db.commit()
        return len(sessions)
    except Exception as exc:
        db.rollback()
        logger.warning("No se pudo purgar historial de sesiones: %s", exc)
        return 0


def _session_to_dict(s: UserSession) -> dict:
    def iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return {
        "jti": s.jti,
        "usuario": s.username,
        "login_method": s.login_method,
        "created_at": iso(s.created_at),
        "expires_at": iso(s.expires_at),
        "last_seen_at": iso(s.last_seen_at),
        "ip": s.ip,
        "user_agent": s.user_agent,
        "revoked": s.revoked,
        "revoked_at": iso(s.revoked_at),
    }
