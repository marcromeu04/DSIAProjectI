"""Cómo se separan los datos para medir sin hacerse trampas.

Dos niveles, como en params.yaml:
1. Test (holdout): los últimos N días. No se usan para nada hasta la evaluación final.
2. Validación cruzada temporal sobre el resto: cada fold entrena con el pasado y valida con
   el bloque siguiente, dejando un hueco de gap horas entre los dos. Nunca se entrena con el
   futuro para predecir el pasado, que es lo que haría un KFold normal.
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from energia_app.config import ValidationConfig
from energia_app.exceptions import ConfigError


def holdout_split(X: pd.DataFrame, y: pd.Series, test_days: int):
    """Separa los últimos test_days días. Devuelve X_train, X_test, y_train, y_test."""
    corte = X.index.max() - pd.Timedelta(days=test_days)
    entreno = X.index <= corte
    if entreno.sum() == 0 or (~entreno).sum() == 0:
        raise ConfigError(f"test_days={test_days} deja vacío el entrenamiento o el test")
    return X[entreno], X[~entreno], y[entreno], y[~entreno]


def time_series_cv(config: ValidationConfig) -> TimeSeriesSplit:
    """Folds temporales con hueco. Con datos horarios, gap en filas = horas."""
    return TimeSeriesSplit(n_splits=config.cv_splits, gap=config.cv_gap_hours)
