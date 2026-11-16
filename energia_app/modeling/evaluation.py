"""Métricas de error de una previsión de precio, en EUR/MWh."""

from __future__ import annotations

import numpy as np


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """MAE (error medio), RMSE (castiga más los errores grandes) y sesgo (si se queda corto o se pasa)."""
    error = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return {
        "mae": round(float(np.mean(np.abs(error))), 3),
        "rmse": round(float(np.sqrt(np.mean(error ** 2))), 3),
        "bias": round(float(np.mean(error)), 3),
    }
