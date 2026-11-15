"""Features de calendario: en qué momento del día, de la semana y del año cae cada hora.

Solo dependen de la fecha, nunca del precio, así que no pueden mirar el futuro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from energia_app.features.base import FeatureBlock
from energia_app.features.registry import register

# (nombre, cómo sacarlo de la fecha local, cuántos valores tiene el ciclo)
_CICLOS = (
    ("hour", lambda t: t.hour, 24),
    ("dow", lambda t: t.dayofweek, 7),  # 0 = lunes
    ("month", lambda t: t.month - 1, 12),
)


@register("calendar")
class CalendarFeatures(FeatureBlock):
    """Hora, día de la semana, mes y fin de semana, en hora local.

    cyclical=True añade seno y coseno de cada ciclo: así un modelo lineal entiende que las
    23:00 y las 00:00 están juntas. integers=True deja también los enteros, que es lo que
    mejor aprovechan los árboles.
    """

    def __init__(self, timezone: str = "Europe/Madrid", cyclical: bool = True, integers: bool = True):
        if not (cyclical or integers):
            raise TypeError("calendar necesita cyclical o integers activado")
        self.timezone, self.cyclical, self.integers = timezone, cyclical, integers

    @property
    def columns(self) -> list[str]:
        cols = []
        for nombre, _, _ in _CICLOS:
            if self.integers:
                cols.append(nombre)
            if self.cyclical:
                cols += [f"{nombre}_sin", f"{nombre}_cos"]
        return cols + ["is_weekend"]

    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        local = instants.tz_convert(self.timezone)
        out = {}
        for nombre, extraer, periodo in _CICLOS:
            valor = np.asarray(extraer(local))
            if self.integers:
                out[nombre] = valor
            if self.cyclical:
                angulo = 2 * np.pi * valor / periodo
                out[f"{nombre}_sin"], out[f"{nombre}_cos"] = np.sin(angulo), np.cos(angulo)
        out["is_weekend"] = (np.asarray(local.dayofweek) >= 5).astype(int)
        return pd.DataFrame(out, index=instants)
