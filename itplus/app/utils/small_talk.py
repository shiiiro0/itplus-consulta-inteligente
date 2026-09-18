"""Detect casual, greeting-only, or conversation-meta user messages."""

from __future__ import annotations

import re

_SMALL_TALK = re.compile(
    r"^(?:"
    r"hola|hello|hi|hey|buenas|buenos\s*d[ií]as|buenas\s*tardes|buenas\s*noches|"
    r"saludos|qu[eé]\s*tal|como\s*est[aá]s|gracias|muchas\s*gracias|ok|vale|perfecto"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)

# Meta-mensajes sobre el saludo / que el bot no entendió el hola.
_GREETING_META = re.compile(
    r"(te\s+salud|solo\s+(te\s+)?salud|era\s+un\s+saludo|solamente\s+salud|"
    r"nada\s+m[aá]s|solo\s+dije\s+hola)",
    re.IGNORECASE,
)

# Preguntas sobre el hilo del chat (no sobre datos de reportes).
_CONVERSATION_META = re.compile(
    r"(?:"
    r"en\s+qu[eé]\s+quedamos|"
    r"d[oó]nde\s+(?:quedamos|est[aá]bamos|vamos)|"
    r"qu[eé]\s+(?:hablamos|revisamos|vimos|dijimos|analizamos)\b|"
    r"de\s+qu[eé]\s+(?:est[aá]bamos|habl[aá]bamos)|"
    r"resum[ea]\s+(?:esta\s+)?(?:conversaci[oó]n|chat|lo\s+(?:hablado|visto|anterior))|"
    r"retom(?:a|emos|ar)\b|"
    r"continuar?\s+(?:donde|desde)|"
    r"contexto\s+de\s+(?:este\s+)?(?:chat|conversaci[oó]n)|"
    r"en\s+qu[eé]\s+(?:est[aá]bamos|ibas|íbamos)"
    r")",
    re.IGNORECASE,
)


def is_small_talk(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 120:
        return False
    if _SMALL_TALK.match(text):
        return True
    # "pero te salude solamente" / "solo dije hola"
    return bool(_GREETING_META.search(text)) and len(text) <= 120


def is_conversation_meta(message: str) -> bool:
    """True when the user asks about the chat thread itself, not about KPIs."""
    text = (message or "").strip()
    if not text or len(text) > 160:
        return False
    if not _CONVERSATION_META.search(text):
        return False
    # Señales fuertes: siempre meta del hilo.
    if re.search(
        r"en\s+qu[eé]\s+quedamos|d[oó]nde\s+(?:quedamos|est[aá]bamos)|"
        r"resum[ea]\s+(?:esta\s+)?(?:conversaci[oó]n|chat)|retom",
        text,
        re.IGNORECASE,
    ):
        return True
    # Señales débiles ("qué vimos"): no si traen vocabulario de BI.
    low = text.lower()
    bi_hints = (
        "venta", "ingreso", "kpi", "q1", "q2", "mes", "total", "proyecc",
        "compar", "margen", "factur", "vendedor", "categor",
    )
    if any(h in low for h in bi_hints):
        return False
    return True
