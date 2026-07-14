"""Editable security settings stored in the database."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from itplus.app.models.app_setting import AppSetting

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, tuple[int, float]] = {}
_CACHE_TTL = 30.0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


SETTINGS_SPEC: dict[str, dict] = {
    "token_expire_hours": {
        "default": _env_int("API_TOKEN_EXPIRE_HOURS", 24),
        "min": 1,
        "max": 720,
        "label": "Duración de la sesión",
        "unit": "horas",
        "help": "Tiempo que permanece válido el inicio de sesión antes de pedir login otra vez.",
    },
    "session_idle_minutes": {
        "default": _env_int("SESSIONS_IDLE_MINUTES", 30),
        "min": 1,
        "max": 1440,
        "label": "Inactividad para marcar como no activa",
        "unit": "minutos",
        "help": "Tras este tiempo sin actividad, la sesión deja de aparecer en Activas.",
    },
    "sessions_retention_months": {
        "default": _env_int("SESSIONS_RETENTION_MONTHS", 6),
        "min": 1,
        "max": 120,
        "label": "Retención del historial",
        "unit": "meses",
        "help": "Antigüedad máxima de los registros de sesión antes de purgarse.",
    },
}


def _clamp(key: str, value: int) -> int:
    spec = SETTINGS_SPEC[key]
    return max(spec["min"], min(spec["max"], int(value)))


def get_int(db: Session, key: str) -> int:
    spec = SETTINGS_SPEC.get(key)
    if spec is None:
        raise KeyError(key)
    default = int(spec["default"])

    now = time.time()
    with _lock:
        cached = _cache.get(key)
        if cached and (now - cached[1]) < _CACHE_TTL:
            return cached[0]

    valor = default
    try:
        row = db.get(AppSetting, key)
        if row and row.value is not None:
            valor = _clamp(key, int(row.value))
    except Exception as exc:
        logger.debug("Config '%s' no leída de BD: %s", key, exc)

    with _lock:
        _cache[key] = (valor, now)
    return valor


def get_all(db: Session) -> list[dict]:
    out: list[dict] = []
    for key, spec in SETTINGS_SPEC.items():
        out.append(
            {
                "clave": key,
                "label": spec["label"],
                "unit": spec["unit"],
                "help": spec["help"],
                "min": spec["min"],
                "max": spec["max"],
                "default": int(spec["default"]),
                "valor": get_int(db, key),
            }
        )
    return out


def set_many(db: Session, values: dict[str, int], usuario: str | None = None) -> tuple[bool, str]:
    try:
        now = datetime.now(timezone.utc)
        for key, raw in values.items():
            if key not in SETTINGS_SPEC:
                continue
            try:
                valor = int(raw)
            except (TypeError, ValueError):
                spec = SETTINGS_SPEC[key]
                return False, f"El valor de '{spec['label']}' debe ser un número entero."
            spec = SETTINGS_SPEC[key]
            if valor < spec["min"] or valor > spec["max"]:
                return (
                    False,
                    f"'{spec['label']}' debe estar entre {spec['min']} y {spec['max']} {spec['unit']}.",
                )
            row = db.get(AppSetting, key)
            if row is None:
                row = AppSetting(key=key)
                db.add(row)
            row.value = str(valor)
            row.updated_at = now
            row.updated_by = usuario
        db.commit()
        with _lock:
            _cache.clear()
        return True, ""
    except Exception as exc:
        db.rollback()
        return False, str(exc)
