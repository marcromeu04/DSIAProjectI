"""Festivos: un festivo nacional se comporta como un domingo (menos consumo, precio más bajo)."""

from __future__ import annotations

import holidays as holidays_lib
import numpy as np
import pandas as pd

from energia_app.features.base import FeatureBlock
from energia_app.features.registry import register


@register("holidays")
class HolidayFeatures(FeatureBlock):
    """is_holiday = 1 si la fecha local es festivo nacional del país indicado.

    Solo festivos nacionales: el precio PVPC es único para toda España, así que un festivo
    de una sola comunidad apenas lo mueve.
    """

    def __init__(self, country: str = "ES", timezone: str = "Europe/Madrid"):
        if country not in holidays_lib.list_supported_countries():
            raise TypeError(f"país no soportado por la librería holidays: {country}")
        self.country, self.timezone = country, timezone

    @property
    def columns(self) -> list[str]:
        return ["is_holiday"]

    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        fechas = instants.tz_convert(self.timezone).date
        calendario = holidays_lib.country_holidays(self.country, years=sorted({d.year for d in fechas}))
        return pd.DataFrame({"is_holiday": np.array([d in calendario for d in fechas], dtype=int)}, index=instants)
