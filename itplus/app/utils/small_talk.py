"""Detect casual or greeting-only user messages."""

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


def is_small_talk(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 120:
        return False
    if _SMALL_TALK.match(text):
        return True
    # "pero te salude solamente" / "solo dije hola"
    return bool(_GREETING_META.search(text)) and len(text) <= 120
