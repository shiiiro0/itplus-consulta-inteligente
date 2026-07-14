"""RAG query endpoints (Motor B)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user, get_optional_user
from itplus.app.core.database import get_db
from itplus.app.core.phases import CURRENT_PHASE, RAG_KNOWLEDGE_CATEGORIES
from itplus.app.models.user import User
from itplus.app.schemas.chat_query import QueryHistoryItem, QueryRequest, QueryResponse
from itplus.app.services.rag import RAGService

router = APIRouter()


@router.get("/roadmap")
def rag_roadmap():
    return {
        "current_phase": CURRENT_PHASE,
        "knowledge_categories": RAG_KNOWLEDGE_CATEGORIES,
    }


@router.post("", response_model=QueryResponse)
def query_documents(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    svc = RAGService(db)
    return svc.query(
        question=payload.question,
        user_id=current_user.id if current_user else None,
        category=payload.category,
    )


@router.get("/history", response_model=list[QueryHistoryItem])
def query_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = RAGService(db)
    logs = svc.get_history(user_id=current_user.id)
    return logs
