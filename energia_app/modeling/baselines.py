"""Baselines: predicciones de referencia que cualquier modelo tiene que batir.

Patrón Strategy + sustitución de Liskov: un baseline es un estimador de sklearn más (fit y
predict), así que se evalúa con exactamente el mismo código que los modelos de verdad.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

from energia_app.exceptions import ConfigError


class NaiveLag(BaseEstimator, RegressorMixin):
    """Predice que el precio será el mismo que hace `hours` horas (lee la columna lag_<hours>h)."""

    def __init__(self, hours: int = 24):
        self.hours = hours

    def fit(self, X: pd.DataFrame, y=None) -> "NaiveLag":
        if self.column not in X.columns:
            raise ConfigError(f"El baseline necesita la feature {self.column}: añádela en el bloque lags")
        self.is_fitted_ = True
        return self

    @property
    def column(self) -> str:
        return f"lag_{self.hours}h"

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X[self.column].to_numpy(dtype=float)


BASELINES = {"naive_24h": lambda: NaiveLag(24), "naive_168h": lambda: NaiveLag(168)}


def build_baseline(name: str) -> NaiveLag:
    if name not in BASELINES:
        raise ConfigError(f"Baseline desconocido: '{name}'. Disponibles: {sorted(BASELINES)}")
    return BASELINES[name]()
