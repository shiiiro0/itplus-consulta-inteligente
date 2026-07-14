from fastapi import APIRouter

from itplus.app.api.v1 import (
    auth,
    chat_assistant,
    chat_bot,
    chat_query,
    documents,
    health,
    history,
    roles,
    sessions,
    settings,
    usuarios,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["ITPlus - Sistema"])
api_router.include_router(auth.router, prefix="/auth", tags=["ITPlus - Auth"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["ITPlus - Usuarios"])
api_router.include_router(roles.router, prefix="/roles", tags=["ITPlus - Roles"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["ITPlus - Sesiones"])
api_router.include_router(settings.router, prefix="/settings", tags=["ITPlus - Configuración"])
api_router.include_router(chat_bot.router, prefix="/chat/bot", tags=["ITPlus - ITPlusBot"])
api_router.include_router(chat_assistant.router, prefix="/chat/assistant", tags=["ITPlus - Asistente"])
api_router.include_router(chat_query.router, prefix="/chat/query", tags=["ITPlus - Consulta RAG"])
api_router.include_router(history.router, prefix="/history", tags=["ITPlus - Historial"])
api_router.include_router(documents.router, prefix="/documents", tags=["ITPlus - Documentos"])
