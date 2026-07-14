"""Managerial assistant API — Phase 1 unified chat."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user
from itplus.app.connectors.registry import list_info
from itplus.app.core.database import get_db
from itplus.app.core.phases import CURRENT_PHASE, KNOWLEDGE_CATEGORIES, ROADMAP_PHASES
from itplus.app.models.user import User
from itplus.app.schemas.assistant import (
    AssistantConversationResponse,
    AssistantMessageRequest,
    AssistantMessageResponse,
)
from itplus.app.services.assistant import AssistantService

router = APIRouter()


@router.post("", response_model=AssistantMessageResponse)
def send_message(
    body: AssistantMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssistantService(db)
    try:
        result = service.send_message(
            message=body.message.strip(),
            conversation_id=body.conversation_id,
            user_id=current_user.id,
            category=body.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/stream")
def stream_message(
    body: AssistantMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssistantService(db)

    def event_stream():
        try:
            for event in service.stream_message(
                message=body.message.strip(),
                conversation_id=body.conversation_id,
                user_id=current_user.id,
                category=body.category,
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Error al procesar la consulta'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/conversations/{conversation_id}/close")
def close_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssistantService(db)
    try:
        service.close_conversation(conversation_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/conversations/{conversation_id}", response_model=AssistantConversationResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssistantService(db)
    detail = service.get_conversation_detail(conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    conv = service.get_conversation(conversation_id)
    if conv and conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta conversación")
    return detail


@router.get("/connectors")
def list_connectors(current_user: User = Depends(get_current_user)):
    return {"connectors": list_info()}


@router.get("/roadmap")
def get_roadmap(current_user: User = Depends(get_current_user)):
    return {
        "phases": ROADMAP_PHASES,
        "current_phase": CURRENT_PHASE,
        "knowledge_categories": KNOWLEDGE_CATEGORIES,
    }
