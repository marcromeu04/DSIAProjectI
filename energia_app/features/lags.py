"""Retardos: el precio de la misma hora hace N horas. Es la información que más pesa."""

from __future__ import annotations

import pandas as pd

from energia_app.features.base import FeatureBlock
from energia_app.features.registry import register


@register("lags")
class LagFeatures(FeatureBlock):
    """lag_24h = precio 24 horas antes, lag_168h = hace una semana a la misma hora, etc.

    Cada retardo debe ser >= horizon_hours. La previsión de mañana se hace hoy: el último
    precio conocido de cada hora de mañana es el de 24 h antes. Un retardo de 1 h sería
    hacer trampa (en producción ese dato aún no existe), así que se rechaza al configurar.
    Los retardos se calculan en UTC: "hace 24 h" es exacto también el día del cambio de hora.
    """

    def __init__(self, hours: list[int], horizon_hours: int = 24):
        if not hours or any((not isinstance(h, int)) or h < horizon_hours for h in hours):
            raise TypeError(f"cada retardo de 'hours' debe ser un entero >= {horizon_hours} (tiene {hours})")
        self.hours, self.horizon_hours = sorted(set(hours)), horizon_hours

    @property
    def columns(self) -> list[str]:
        return [f"lag_{h}h" for h in self.hours]

    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        return pd.DataFrame(
            {f"lag_{h}h": prices.reindex(instants - pd.Timedelta(hours=h)).to_numpy() for h in self.hours},
            index=instants,
        )
