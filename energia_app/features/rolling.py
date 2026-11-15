"""Ventanas móviles: nivel y volatilidad recientes del precio, vistos desde el último dato conocido."""

from __future__ import annotations

import pandas as pd

from energia_app.features.base import FeatureBlock
from energia_app.features.registry import register

_STATS = frozenset({"mean", "std", "min", "max"})


@register("rolling")
class RollingFeatures(FeatureBlock):
    """roll_mean_168h = media de los precios de la semana que acaba shift_hours antes.

    Dicen al modelo si estamos en una racha cara o barata (media) y si el mercado está
    tranquilo o movido (desviación). La ventana termina shift_hours antes del instante
    (24 h por defecto), así que solo usa precios ya publicados al hacer la previsión.
    """

    def __init__(self, windows_hours: list[int], shift_hours: int = 24, stats: list[str] | None = None,
                 horizon_hours: int = 24):
        stats = stats or ["mean", "std"]
        if shift_hours < horizon_hours:
            raise TypeError(f"shift_hours debe ser >= {horizon_hours} para no usar precios futuros")
        if not windows_hours or any((not isinstance(w, int)) or w < 2 for w in windows_hours):
            raise TypeError(f"cada ventana de 'windows_hours' debe ser un entero >= 2 (tiene {windows_hours})")
        if not set(stats) <= _STATS:
            raise TypeError(f"stats solo admite {sorted(_STATS)} (tiene {stats})")
        self.windows_hours, self.shift_hours, self.stats = sorted(set(windows_hours)), shift_hours, list(stats)

    @property
    def columns(self) -> list[str]:
        return [f"roll_{s}_{w}h" for w in self.windows_hours for s in self.stats]

    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        fin_ventana = instants - pd.Timedelta(hours=self.shift_hours)
        out = {}
        for w in self.windows_hours:
            # Ventana por tiempo ("168h"), no por filas: no se descuadra si falta alguna hora
            ventana = prices.rolling(f"{w}h", min_periods=max(2, w // 2))
            for s in self.stats:
                out[f"roll_{s}_{w}h"] = getattr(ventana, s)().reindex(fin_ventana).to_numpy()
        return pd.DataFrame(out, index=instants)
