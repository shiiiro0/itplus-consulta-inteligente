"""Deterministic short-horizon revenue forecast (no heavy ML deps).

Uses the monthly series already produced by CRISP/DuckDB, then applies a
simple method the gerente can audit:
  - 3-month moving average, or
  - linear trend (least squares)

Chooses the method with lower one-step MAPE on a tiny backtest when possible.
This is NOT Prophet/ARIMA — it is an honest first forecast layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ForecastResult:
    rows: list[dict[str, Any]]
    method: str
    method_label: str
    horizon_label: str
    point_forecast: float
    low: float
    high: float
    mape_pct: float | None
    assumptions: list[str]
    limitations: list[str]


def _parse_month_key(label: str) -> tuple[int, int] | None:
    parts = str(label).split("-")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _next_month_label(last_label: str) -> str:
    parsed = _parse_month_key(last_label)
    if not parsed:
        return "próximo período"
    year, month = parsed
    if month == 12:
        return f"{year + 1}-01"
    return f"{year}-{month + 1:02d}"


def _moving_average(values: list[float], window: int = 3) -> float:
    w = min(window, len(values))
    return float(np.mean(values[-w:]))


def _linear_forecast(values: list[float]) -> float:
    n = len(values)
    x = np.arange(n, dtype=float)
    y = np.asarray(values, dtype=float)
    # y = a + b*x ; predict x=n
    b, a = np.polyfit(x, y, 1)
    return float(a + b * n)


def _one_step_mape(values: list[float], method: str) -> float | None:
    """Hold out the last point; forecast it from the rest; return MAPE %."""
    if len(values) < 4:
        return None
    train, actual = values[:-1], values[-1]
    if actual == 0:
        return None
    if method == "moving_average":
        pred = _moving_average(train)
    else:
        pred = _linear_forecast(train)
    return abs(pred - actual) / abs(actual) * 100.0


def build_revenue_forecast(monthly_rows: list[dict[str, Any]]) -> ForecastResult | None:
    """Enrich monthly SUM(revenue) rows with a next-month projection."""
    series: list[tuple[str, float]] = []
    for row in monthly_rows:
        label = str(row.get("label") or "").strip()
        try:
            value = float(row.get("value") or 0)
        except (TypeError, ValueError):
            continue
        if not label or value < 0:
            continue
        series.append((label, value))

    if len(series) < 3:
        return None

    labels = [s[0] for s in series]
    values = [s[1] for s in series]
    horizon = _next_month_label(labels[-1])

    ma_mape = _one_step_mape(values, "moving_average")
    lin_mape = _one_step_mape(values, "linear")

    # Prefer the method with lower backtest error when both exist.
    if ma_mape is not None and lin_mape is not None:
        use_linear = lin_mape <= ma_mape
    elif lin_mape is not None:
        use_linear = True
    elif ma_mape is not None:
        use_linear = False
    else:
        # Too short for backtest: linear if clear trend, else MA.
        if len(values) >= 4 and values[-1] > values[0] * 1.05:
            use_linear = True
        elif len(values) >= 4 and values[-1] < values[0] * 0.95:
            use_linear = True
        else:
            use_linear = False

    if use_linear:
        point = _linear_forecast(values)
        method = "linear_trend"
        method_label = "tendencia lineal (mínimos cuadrados) sobre la serie mensual"
        mape = lin_mape
    else:
        point = _moving_average(values, 3)
        method = "moving_average_3"
        method_label = "promedio móvil de los últimos 3 meses"
        mape = ma_mape

    # Never project negative revenue.
    point = max(0.0, point)

    # Uncertainty band: ± max(10%, last residual MAPE, residual std / mean).
    residuals = []
    if len(values) >= 4:
        for i in range(3, len(values)):
            hist = values[:i]
            actual = values[i]
            pred = _linear_forecast(hist) if use_linear else _moving_average(hist, 3)
            if actual:
                residuals.append(abs(pred - actual) / abs(actual))
    band = 0.10
    if residuals:
        band = max(band, float(np.mean(residuals)))
    if mape is not None:
        band = max(band, mape / 100.0)
    band = min(band, 0.35)  # cap so we don't look absurdly uncertain

    low = max(0.0, point * (1 - band))
    high = point * (1 + band)

    hist_rows = [{"label": lab, "value": round(val, 2), "kind": "historico"} for lab, val in series]
    forecast_row = {
        "label": horizon,
        "value": round(point, 2),
        "kind": "proyeccion",
        "low": round(low, 2),
        "high": round(high, 2),
    }

    assumptions = [
        "Se proyecta solo el siguiente mes calendario a partir de la serie mensual de ingresos (CLP).",
        f"Método elegido: {method_label}.",
        "No incorpora campañas futuras, quiebres de stock, feriados ni cambios de precio no observados.",
    ]
    limitations = [
        "Horizonte corto (1 mes). No usar para presupuesto anual sin validar con el negocio.",
        "Es una proyección estadística simple, no un modelo causal ni machine learning avanzado.",
    ]
    if mape is not None:
        assumptions.append(
            f"Error histórico aproximado (backtest 1 paso): MAPE {mape:.1f}%."
        )
    else:
        limitations.append(
            "Serie corta: no hubo suficientes meses para medir error histórico con rigor."
        )

    return ForecastResult(
        rows=hist_rows + [forecast_row],
        method=method,
        method_label=method_label,
        horizon_label=horizon,
        point_forecast=round(point, 2),
        low=round(low, 2),
        high=round(high, 2),
        mape_pct=round(mape, 1) if mape is not None else None,
        assumptions=assumptions,
        limitations=limitations,
    )
