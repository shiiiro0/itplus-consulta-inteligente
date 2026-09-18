"""Best-effort text decoding for documents with an unknown/unlabeled encoding.

Antes `parse_csv`/`parse_txt` en `ingestion.py` asumían UTF-8 a la fuerza con
`errors="ignore"`. Muchos CSV exportados desde Excel en configuración
regional Chile/LatAm (o guardados hace años en Windows) vienen en
`windows-1252`/`latin-1`, no en UTF-8 — cualquier byte >= 0x80 que no forme
una secuencia UTF-8 válida (que es el caso típico de una tilde o "ñ" en esos
encodings) se descartaba en silencio, así que palabras como "Descripción" o
"Ñuñoa" quedaban truncadas/corruptas sin ningún error visible.
"""

from __future__ import annotations

from pathlib import Path

# Orden importa: probamos UTF-8 estricto primero (la mayoría de los archivos
# modernos ya vienen así); si falla, probamos cp1252 (el encoding más común
# para exports viejos de Excel/Windows en español); latin-1 nunca falla
# (mapea cualquier byte 0-255 1:1), así que es la red de seguridad final.
_ENCODINGS_TO_TRY = ("utf-8", "cp1252", "latin-1")


def read_text_best_effort(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for encoding in _ENCODINGS_TO_TRY:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    # No debería llegar acá (latin-1 siempre decodifica), pero por si acaso
    # no perdemos el archivo completo.
    return raw.decode("utf-8", errors="replace")
