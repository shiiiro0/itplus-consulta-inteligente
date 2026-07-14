"""CRISP-DM Phase 2: Data Understanding — summarize registered datasets."""

from __future__ import annotations

from itplus.app.services.crisp_analyst.models import CrispStep, DatasetProfile


def profile_step(profile: DatasetProfile) -> CrispStep:
    cols = ", ".join(profile.columns[:8])
    if len(profile.columns) > 8:
        cols += f" (+{len(profile.columns) - 8} más)"
    detail = (
        f"{profile.row_count:,} filas · columnas: {cols}"
        if profile.row_count
        else "Sin filas"
    )
    if profile.date_min and profile.date_max:
        detail += f" · rango {profile.date_min} → {profile.date_max}"
    return CrispStep(
        phase="data_understanding",
        label="Comprensión de datos",
        detail=detail,
    )


def select_best_dataset(
    candidates: list[tuple[object, DatasetProfile]],
    question: str,
) -> tuple[object, DatasetProfile] | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    q = question.lower()
    scored: list[tuple[int, object, DatasetProfile]] = []
    for doc, profile in candidates:
        score = 0
        name = (getattr(doc, "filename", "") or "").lower()
        if any(tok in name for tok in q.split() if len(tok) > 3):
            score += 3
        if "venta" in q and "venta" in name:
            score += 2
        if "ecommerce" in name or "sales" in name:
            score += 1
        score += min(profile.row_count // 500, 5)
        scored.append((score, doc, profile))

    scored.sort(key=lambda x: x[0], reverse=True)
    _, doc, profile = scored[0]
    return doc, profile
