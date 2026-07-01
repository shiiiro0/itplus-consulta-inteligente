from fastapi import APIRouter

from itplus.app.api.v1 import auth, chat_bot, chat_query, documents, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["ITPlus - Sistema"])
api_router.include_router(auth.router, prefix="/auth", tags=["ITPlus - Auth"])
api_router.include_router(chat_bot.router, prefix="/chat/bot", tags=["ITPlus - ITPlusBot"])
api_router.include_router(chat_query.router, prefix="/chat/query", tags=["ITPlus - Consulta RAG"])
api_router.include_router(documents.router, prefix="/documents", tags=["ITPlus - Documentos"])
