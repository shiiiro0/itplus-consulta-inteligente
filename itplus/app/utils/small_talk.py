"""Detect casual, greeting, meta, off-topic, or non-BI chat messages."""

from __future__ import annotations

import re

_SMALL_TALK = re.compile(
    r"^(?:"
    r"hola|hello|hi|hey|buenas|buenos\s*d[ií]as|buenas\s*tardes|buenas\s*noches|"
    r"saludos|qu[eé]\s*tal|como\s*est[aá]s|gracias|muchas\s*gracias|ok|vale|perfecto|"
    r"de\s*acuerdo|entendid[oa]|listo|claro"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)

_GREETING_META = re.compile(
    r"(te\s+salud|solo\s+(te\s+)?salud|era\s+un\s+saludo|solamente\s+salud|"
    r"nada\s+m[aá]s|solo\s+dije\s+hola)",
    re.IGNORECASE,
)

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

_IDENTITY = re.compile(
    r"^(?:"
    r"qui[eé]n\s+(?:eres|sos)|qu[eé]\s+(?:eres|sos)|"
    r"c[oó]mo\s+te\s+llamas|tu\s+nombre|"
    r"qu[eé]\s+puedes\s+(?:hacer|ayudar)|para\s+qu[eé]\s+(?:sirves|est[aá]s)|"
    r"cu[aá]l\s+es\s+tu\s+(?:rol|funci[oó]n)"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)

_CAPABILITY = re.compile(
    r"(?:"
    r"no\s+se\s+puede\s+convers|"
    r"no\s+(?:sirves|funcionas|ayudas|entiendes)|"
    r"por\s+qu[eé]\s+no\b|"
    r"no\s+(?:me\s+)?(?:responden?|contestan?)|"
    r"puedes\s+(?:hablar|conversar|chatear)|"
    r"solo\s+(?:sirves|respondes)\s+para|"
    r"eres\s+(?:un\s+)?(?:in[uú]til|malo|tonto)|"
    r"no\s+sirve\s+(?:de\s+)?nada|"
    r"falla\s+todo|siempre\s+(?:fallas|error)"
    r")",
    re.IGNORECASE,
)

_OFF_TOPIC = re.compile(
    r"(?:"
    r"opin[aá]s?\s+(?:del|de\s+la|de\s+los|sobre)|"
    r"qu[eé]\s+piensas\s+(?:del|de\s+la|sobre)|"
    r"\bmundo\b|\bclima\b|\bchiste\b|chistes|"
    r"f[uú]tbol|futbol|pol[ií]tica|filosof|"
    r"religi[oó]n|receta|pel[ií]cula|serie\b|"
    r"cu[eé]ntame\s+(?:un|una|algo)|"
    r"c[oó]mo\s+est[aá]\s+el\s+d[ií]a|"
    r"habla(?:mos)?\s+de\s+(?:otra|cualquier)\s+cosa|"
    r"tema\s+libre|charlar\s+de"
    r")",
    re.IGNORECASE,
)

_BI_HINTS = (
    "venta", "vend", "ingreso", "factur", "kpi", "margen", "ticket",
    "q1", "q2", "q3", "q4", "trimestre", "mes", "año", "anio",
    "compar", "versus", " vs", "tendencia", "evoluci", "proyecc",
    "forecast", "pronostic", "predic", "total", "cuanto", "cuánto",
    "cuantos", "cuántos", "vendedor", "categor", "producto", "region",
    "región", "quiebre", "wms", "sap", "reporte", "documento",
    "gráfico", "grafico", "desglose", "unidad", "meta", "aov",
    "pedido", "orden", "stock", "inventario", "cliente", "canal",
)


def is_small_talk(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 120:
        return False
    if _SMALL_TALK.match(text):
        return True
    return bool(_GREETING_META.search(text)) and len(text) <= 120


def is_conversation_meta(message: str) -> bool:
    """True when the user asks about the chat thread itself, not about KPIs."""
    text = (message or "").strip()
    if not text or len(text) > 160:
        return False
    if not _CONVERSATION_META.search(text):
        return False
    if re.search(
        r"en\s+qu[eé]\s+quedamos|d[oó]nde\s+(?:quedamos|est[aá]bamos)|"
        r"resum[ea]\s+(?:esta\s+)?(?:conversaci[oó]n|chat)|retom",
        text,
        re.IGNORECASE,
    ):
        return True
    low = text.lower()
    if any(h in low for h in _BI_HINTS):
        return False
    return True


def looks_like_bi_question(message: str) -> bool:
    low = (message or "").lower()
    if not low.strip():
        return False
    return any(h in low for h in _BI_HINTS)


def is_identity_question(message: str) -> bool:
    text = (message or "").strip()
    return bool(text) and bool(_IDENTITY.match(text))


def is_capability_or_frustration(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 180:
        return False
    return bool(_CAPABILITY.search(text))


def is_off_topic(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 200:
        return False
    if looks_like_bi_question(text):
        return False
    return bool(_OFF_TOPIC.search(text))


def needs_static_chat_reply(message: str) -> bool:
    """Non-BI chatter that should not burn LLM quota or retrieval."""
    if is_small_talk(message) or is_conversation_meta(message):
        return False
    if is_identity_question(message) or is_capability_or_frustration(message):
        return True
    if is_off_topic(message):
        return True
    return False
