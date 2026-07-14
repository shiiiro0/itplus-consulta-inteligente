"""Unified chat history API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user
from itplus.app.core.database import get_db
from itplus.app.models.user import User
from itplus.app.schemas.history import (
    ChatExportResponse,
    ChatHistoryItem,
    ChatHistoryListResponse,
    ConsultaDetailResponse,
    RenameChatRequest,
)
from itplus.app.services import history_service

router = APIRouter()


@router.get("/chats", response_model=ChatHistoryListResponse)
def list_chats(
    chat_type: str | None = Query(
        default=None,
        description="Filtrar: asistente, bot, consulta",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if chat_type and chat_type not in history_service.CHAT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de chat inválido")
    items = history_service.list_chats(db, current_user.id, chat_type=chat_type)
    return ChatHistoryListResponse(
        items=[ChatHistoryItem.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/chats/consulta/{log_id}", response_model=ConsultaDetailResponse)
def get_consulta_detail(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = history_service.get_consulta_detail(db, log_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return detail


@router.patch("/chats/{chat_type}/{chat_id}")
def rename_chat(
    chat_type: str,
    chat_id: uuid.UUID,
    payload: RenameChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if chat_type not in history_service.CHAT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de chat inválido")
    ok = history_service.rename_chat(db, chat_id, chat_type, current_user.id, payload.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return {"ok": True, "title": payload.title.strip()[:255]}


@router.delete("/chats/{chat_type}/{chat_id}")
def delete_chat(
    chat_type: str,
    chat_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if chat_type not in history_service.CHAT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de chat inválido")
    ok = history_service.delete_chat(db, chat_id, chat_type, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return {"ok": True}


@router.get("/chats/{chat_type}/{chat_id}/export", response_model=ChatExportResponse)
def export_chat(
    chat_type: str,
    chat_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if chat_type not in history_service.CHAT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de chat inválido")
    result = history_service.export_chat(db, chat_id, chat_type, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return result
