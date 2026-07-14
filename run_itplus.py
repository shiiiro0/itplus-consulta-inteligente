"""
ITPlus — Plataforma Universal de Consulta Inteligente
Standalone FastAPI entry point for Docker and development.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from itplus.app.api.deps import get_current_token_user
from itplus.app.api.v1.router import api_router
from itplus.app.core.config import get_settings
from itplus.app.core.database import SessionLocal, init_db
from itplus.app.core.security import decode_access_token
from itplus.app.services.rbac import ADMIN_ROLE, get_permisos_for_role

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Plataforma de consulta inteligente con Asistente Gerencial, ITPlusBot y RAG",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

_origins_raw = os.environ.get(
    "API_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8000",
)
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODULE_PREFIXES: list[tuple[str, str]] = [
    ("/api/v1/chat/assistant", "asistente"),
    ("/api/v1/chat/bot", "bot"),
    ("/api/v1/chat/query", "consulta"),
    ("/api/v1/history", "historial"),
    ("/api/v1/documents", "documentos"),
    ("/api/v1/usuarios", "usuarios"),
    ("/api/v1/roles", "roles"),
    ("/api/v1/sessions", "sesiones"),
    ("/api/v1/settings", "sesiones"),
]

PUBLIC_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/azure",
    "/api/v1/auth/azure/status",
    "/api/v1/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
)


class ModulePermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/v1") or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return await call_next(request)

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
        except ValueError:
            return await call_next(request)

        rol = str(payload.get("rol", ""))
        if rol.lower() == ADMIN_ROLE.lower():
            return await call_next(request)

        modulo: str | None = None
        for prefix, mod in MODULE_PREFIXES:
            if path.startswith(prefix):
                modulo = mod
                break
        if modulo is None:
            return await call_next(request)

        db = SessionLocal()
        try:
            permisos = get_permisos_for_role(db, rol)
        finally:
            db.close()

        if modulo not in permisos:
            return JSONResponse(
                status_code=403,
                content={"detail": f"No tienes permiso para acceder al módulo '{modulo}'."},
            )
        return await call_next(request)


app.add_middleware(ModulePermissionMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing ITPlus database...")
    init_db()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _warmup_ai_stack)

    logger.info("%s started successfully", settings.app_name)


def _warmup_ai_stack() -> None:
    from itplus.app.services.embedding import warmup_embedding_model
    from itplus.app.services.llm_provider import llm_provider

    warmup_embedding_model()
    _ = llm_provider.client
    logger.info("LLM client initialized")


_public_dir = Path(__file__).parent / "public"
if _public_dir.exists():
    app.mount("/", StaticFiles(directory=str(_public_dir), html=True), name="itplus-public")
