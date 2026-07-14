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


def is_small_talk(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 80:
        return False
    return bool(_SMALL_TALK.match(text))
