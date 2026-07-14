"""Unified chat history for Historial page."""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from itplus.app.models.conversation import Conversation, Message
from itplus.app.models.query_log import QueryLog
from itplus.app.services.assistant import ASSISTANT_CONTEXT_TYPE

CHAT_TYPES = {
    "asistente": "Asistente Gerencial",
    "bot": "ITPlusBot",
    "consulta": "Consulta RAG",
}

DEDUPE_WINDOW = timedelta(hours=24)
CONSULTA_SESSION_GAP = timedelta(minutes=45)


def _preview(text: str, max_len: int = 120) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _normalize_title(text: str) -> str:
    """Normalize for dedupe: ignore case, accents, punctuation."""
    t = unicodedata.normalize("NFKD", (text or "").strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"[^a-z0-9 ]", "", t).strip()


def _conversation_type(context_type: str | None) -> str:
    if context_type == ASSISTANT_CONTEXT_TYPE:
        return "asistente"
    return "bot"


def _last_activity(db: Session, conv: Conversation) -> datetime:
    msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    return msg.created_at if msg else conv.created_at


def _consolidate_active_assistant_sessions(db: Session, user_id: uuid.UUID) -> None:
    """Only one assistant session should stay active per user."""
    actives = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.context_type == ASSISTANT_CONTEXT_TYPE,
            Conversation.status == "active",
        )
        .all()
    )
    if len(actives) <= 1:
        return

    actives.sort(key=lambda c: _last_activity(db, c), reverse=True)
    now = datetime.now(timezone.utc)
    for conv in actives[1:]:
        conv.status = "finished"
        conv.finished_at = now
    db.commit()


def _close_conversations(db: Session, conversation_ids: list[str]) -> None:
    if not conversation_ids:
        return
    now = datetime.now(timezone.utc)
    ids = [uuid.UUID(cid) for cid in conversation_ids]
    rows = (
        db.query(Conversation)
        .filter(Conversation.id.in_(ids), Conversation.status == "active")
        .all()
    )
    for conv in rows:
        conv.status = "finished"
        conv.finished_at = now
    if rows:
        db.commit()


def _dedupe_superseded_assistant_sessions(items: list[dict]) -> tuple[list[dict], list[str]]:
    """Keep one entry per session when the same chat was split across duplicate conversations."""
    assistant = [i for i in items if i["chat_type"] == "asistente"]
    other = [i for i in items if i["chat_type"] != "asistente"]
    if len(assistant) <= 1:
        return items, []

    groups: dict[str, list[dict]] = {}
    for item in assistant:
        key = _normalize_title(item["title"])
        groups.setdefault(key, []).append(item)

    kept: list[dict] = []
    dropped_ids: list[str] = []

    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue

        times = [g["created_at"] for g in group if g.get("created_at")]
        if times and max(times) - min(times) > DEDUPE_WINDOW:
            kept.extend(group)
            continue

        group.sort(
            key=lambda x: (
                x.get("exchange_count", 0),
                x.get("updated_at") or x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        kept.append(group[0])
        dropped_ids.extend(item["id"] for item in group[1:])

    return kept + other, dropped_ids


def _assistant_question_keys(items: list[dict]) -> set[str]:
    keys: set[str] = set()
    for item in items:
        if item["chat_type"] != "asistente":
            continue
        keys.add(_normalize_title(item["title"]))
        for q in item.get("user_questions", []):
            keys.add(_normalize_title(q))
    return keys


def _dedupe_consulta_against_assistant(items: list[dict]) -> list[dict]:
    """Hide RAG logs that duplicate questions already in an assistant session."""
    assistant_keys = _assistant_question_keys(items)
    if not assistant_keys:
        return items

    kept: list[dict] = []
    for item in items:
        if item["chat_type"] != "consulta":
            kept.append(item)
            continue
        log_keys = {_normalize_title(item["title"])}
        for q in item.get("user_questions", []):
            log_keys.add(_normalize_title(q))
        if log_keys & assistant_keys:
            continue
        kept.append(item)
    return kept


def _group_consulta_logs(logs: list[QueryLog]) -> list[dict]:
    """Group one-shot RAG queries into sessions by time proximity."""
    if not logs:
        return []

    ordered = sorted(logs, key=lambda log: log.created_at)
    groups: list[list[QueryLog]] = [[ordered[0]]]
    for log in ordered[1:]:
        if log.created_at - groups[-1][-1].created_at <= CONSULTA_SESSION_GAP:
            groups[-1].append(log)
        else:
            groups.append([log])

    items: list[dict] = []
    for group in reversed(groups):
        first, last = group[0], group[-1]
        count = len(group)
        if first.custom_title:
            title = first.custom_title
        elif count > 1:
            title = f"Sesión RAG ({count} consultas)"
        else:
            title = _preview(first.question, 80)
        items.append(
            {
                "id": str(first.id),
                "chat_type": "consulta",
                "chat_type_label": CHAT_TYPES["consulta"],
                "title": title,
                "preview": _preview(last.answer_summary, 140),
                "message_count": count,
                "exchange_count": count,
                "status": "completed",
                "created_at": first.created_at,
                "updated_at": last.created_at,
                "sources_count": sum(log.sources_count or 0 for log in group),
                "user_questions": [log.question for log in group],
                "session_log_ids": [str(log.id) for log in group],
            }
        )
    return items


def _consulta_session_logs(db: Session, log: QueryLog, user_id: uuid.UUID) -> list[QueryLog]:
    """All query logs in the same RAG session as the given log."""
    window_start = log.created_at - CONSULTA_SESSION_GAP
    window_end = log.created_at + CONSULTA_SESSION_GAP
    candidates = (
        db.query(QueryLog)
        .filter(
            QueryLog.user_id == user_id,
            (QueryLog.chat_type == "consulta") | (QueryLog.chat_type.is_(None)),
            QueryLog.created_at >= window_start,
            QueryLog.created_at <= window_end,
        )
        .order_by(QueryLog.created_at.asc())
        .all()
    )
    if not candidates:
        return [log]

    groups: list[list[QueryLog]] = [[candidates[0]]]
    for row in candidates[1:]:
        if row.created_at - groups[-1][-1].created_at <= CONSULTA_SESSION_GAP:
            groups[-1].append(row)
        else:
            groups.append([row])

    for group in groups:
        if any(row.id == log.id for row in group):
            return group
    return [log]


def list_chats(
    db: Session,
    user_id: uuid.UUID,
    chat_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    _consolidate_active_assistant_sessions(db, user_id)

    items: list[dict] = []

    conv_query = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit * 2)
    )
    conversations = conv_query.all()

    for conv in conversations:
        ctype = _conversation_type(conv.context_type)
        if chat_type and ctype != chat_type:
            continue

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        user_msgs = [m for m in messages if m.role == "user" and (m.content or "").strip()]
        asst_msgs = [m for m in messages if m.role == "assistant"]

        if not user_msgs:
            continue

        title = (conv.title or _preview(user_msgs[0].content, 80)).strip()
        preview = _preview(asst_msgs[-1].content if asst_msgs else "", 140)
        last_at = messages[-1].created_at if messages else conv.created_at
        exchange_count = len(user_msgs)

        items.append(
            {
                "id": str(conv.id),
                "chat_type": ctype,
                "chat_type_label": CHAT_TYPES[ctype],
                "title": title,
                "preview": preview,
                "message_count": exchange_count,
                "exchange_count": exchange_count,
                "status": conv.status,
                "created_at": conv.created_at,
                "updated_at": last_at,
                "user_questions": [m.content for m in user_msgs],
            }
        )

    if not chat_type or chat_type == "consulta":
        logs = (
            db.query(QueryLog)
            .filter(
                QueryLog.user_id == user_id,
                (QueryLog.chat_type == "consulta") | (QueryLog.chat_type.is_(None)),
            )
            .order_by(QueryLog.created_at.desc())
            .limit(limit * 3)
            .all()
        )
        items.extend(_group_consulta_logs(logs))

    items, dropped_ids = _dedupe_superseded_assistant_sessions(items)
    _close_conversations(db, dropped_ids)

    if chat_type is None:
        items = _dedupe_consulta_against_assistant(items)

    items.sort(key=lambda x: x["updated_at"] or x["created_at"], reverse=True)
    return items[:limit]


def get_consulta_detail(db: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
    log = (
        db.query(QueryLog)
        .filter(QueryLog.id == log_id, QueryLog.user_id == user_id)
        .first()
    )
    if not log:
        return None

    session_logs = _consulta_session_logs(db, log, user_id)
    if len(session_logs) == 1:
        return {
            "id": str(log.id),
            "chat_type": "consulta",
            "question": log.question,
            "answer": log.answer_summary,
            "sources_count": log.sources_count,
            "created_at": log.created_at,
            "entries": None,
        }

    entries = [
        {
            "question": row.question,
            "answer": row.answer_summary,
            "sources_count": row.sources_count,
            "created_at": row.created_at,
        }
        for row in session_logs
    ]
    return {
        "id": str(session_logs[0].id),
        "chat_type": "consulta",
        "question": session_logs[0].question,
        "answer": session_logs[-1].answer_summary,
        "sources_count": sum(row.sources_count or 0 for row in session_logs),
        "created_at": session_logs[0].created_at,
        "entries": entries,
    }


def rename_chat(
    db: Session,
    chat_id: uuid.UUID,
    chat_type: str,
    user_id: uuid.UUID,
    title: str,
) -> bool:
    clean = (title or "").strip()[:255]
    if not clean:
        return False

    if chat_type in ("asistente", "bot"):
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == chat_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            return False
        conv.title = clean
        db.commit()
        return True

    if chat_type == "consulta":
        log = (
            db.query(QueryLog)
            .filter(QueryLog.id == chat_id, QueryLog.user_id == user_id)
            .first()
        )
        if not log:
            return False
        session_logs = _consulta_session_logs(db, log, user_id)
        session_logs[0].custom_title = clean
        db.commit()
        return True

    return False


def delete_chat(
    db: Session,
    chat_id: uuid.UUID,
    chat_type: str,
    user_id: uuid.UUID,
) -> bool:
    if chat_type in ("asistente", "bot"):
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == chat_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True

    if chat_type == "consulta":
        log = (
            db.query(QueryLog)
            .filter(QueryLog.id == chat_id, QueryLog.user_id == user_id)
            .first()
        )
        if not log:
            return False
        session_logs = _consulta_session_logs(db, log, user_id)
        for row in session_logs:
            db.delete(row)
        db.commit()
        return True

    return False


def export_chat(
    db: Session,
    chat_id: uuid.UUID,
    chat_type: str,
    user_id: uuid.UUID,
) -> dict | None:
    label = CHAT_TYPES.get(chat_type, chat_type)

    if chat_type in ("asistente", "bot"):
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == chat_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            return None

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        title = conv.title or (
            _preview(messages[0].content, 80) if messages else str(conv.id)[:8]
        )
        lines = [f"# {label}: {title}", f"Exportado: {datetime.now(timezone.utc).isoformat()}", ""]
        for msg in messages:
            role = "Usuario" if msg.role == "user" else "Asistente"
            lines.append(f"## {role}")
            lines.append(msg.content)
            lines.append("")
        safe = re.sub(r"[^\w\-]+", "_", title)[:40] or "conversacion"
        return {
            "filename": f"itplus_{chat_type}_{safe}.txt",
            "content": "\n".join(lines).strip() + "\n",
        }

    if chat_type == "consulta":
        log = (
            db.query(QueryLog)
            .filter(QueryLog.id == chat_id, QueryLog.user_id == user_id)
            .first()
        )
        if not log:
            return None

        session_logs = _consulta_session_logs(db, log, user_id)
        title = session_logs[0].custom_title or _preview(session_logs[0].question, 80)
        lines = [f"# {label}: {title}", f"Exportado: {datetime.now(timezone.utc).isoformat()}", ""]
        for idx, row in enumerate(session_logs, start=1):
            lines.append(f"## Consulta {idx}")
            lines.append(f"Pregunta: {row.question}")
            lines.append("")
            lines.append(f"Respuesta: {row.answer_summary}")
            if row.sources_count:
                lines.append(f"Fuentes: {row.sources_count}")
            lines.append("")
        safe = re.sub(r"[^\w\-]+", "_", title)[:40] or "consulta"
        return {
            "filename": f"itplus_consulta_{safe}.txt",
            "content": "\n".join(lines).strip() + "\n",
        }

    return None
