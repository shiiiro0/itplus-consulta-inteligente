"""
ITPlus — Plataforma Universal de Consulta Inteligente
Standalone FastAPI entry point for Docker and development.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from itplus.app.api.v1.router import api_router
from itplus.app.core.config import get_settings
from itplus.app.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Plataforma de consulta inteligente con ITPlusBot y RAG",
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

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing ITPlus database...")
    init_db()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("%s started successfully", settings.app_name)


# Serve frontend build if available (production)
_public_dir = Path(__file__).parent / "public"
if _public_dir.exists():
    app.mount("/", StaticFiles(directory=str(_public_dir), html=True), name="itplus-public")
