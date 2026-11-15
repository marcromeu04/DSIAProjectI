"""Construcción de la tabla de features a partir de la configuración.

Patrón Composite: FeatureBuilder es también un FeatureBlock (mismo transform), hecho de
otros bloques. El entrenamiento solo habla con él y no sabe qué bloques hay dentro, así que
añadir o quitar bloques en params.yaml no le afecta (inversión de dependencias).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from energia_app.config import FeatureSpec
from energia_app.exceptions import FeatureError
from energia_app.features.base import FeatureBlock
from energia_app.features.registry import create_block


class FeatureBuilder(FeatureBlock):
    name = "builder"

    def __init__(self, blocks: Sequence[FeatureBlock]):
        if not blocks:
            raise FeatureError("FeatureBuilder necesita al menos un bloque")
        columnas = [c for b in blocks for c in b.columns]
        repetidas = sorted({c for c in columnas if columnas.count(c) > 1})
        if repetidas:
            raise FeatureError(f"Hay bloques que generan las mismas columnas: {repetidas}")
        self.blocks = list(blocks)

    @classmethod
    def from_config(cls, specs: Sequence[FeatureSpec], timezone: str) -> "FeatureBuilder":
        """Crea los bloques que pide params.yaml, inyectando la zona horaria a quien la use."""
        return cls([create_block(s, context={"timezone": timezone}) for s in specs])

    @property
    def columns(self) -> list[str]:
        return [c for b in self.blocks for c in b.columns]

    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        return pd.concat([b.transform(prices, instants) for b in self.blocks], axis=1)

    def training_table(self, prices: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        """Features y precio real de cada hora del histórico, sin las horas que no tienen
        historia suficiente (la primera semana, si hay retardos de 168 h)."""
        tabla = self.transform(prices, prices.index)
        completas = tabla.notna().all(axis=1)
        return tabla[completas], prices[completas]

    def forecast_table(self, prices: pd.Series, timezone: str) -> pd.DataFrame:
        """Features de cada hora del día local siguiente al último dato.

        Se cuenta en días de calendario (DateOffset), no en 24 h exactas: el día del cambio
        de hora tiene 23 o 25 horas y no hay que saltárselo.
        """
        ultimo = prices.index.max().tz_convert(timezone)
        inicio = ultimo.normalize() + pd.DateOffset(days=1)
        horas = pd.date_range(inicio, inicio + pd.DateOffset(days=1), freq="h", inclusive="left").tz_convert("UTC")
        tabla = self.transform(prices, horas)
        if tabla.isna().any().any():
            faltan = tabla.columns[tabla.isna().any()].tolist()
            raise FeatureError(f"No hay historia suficiente para predecir mañana (faltan {faltan})")
        return tabla


def price_series(prices: pd.DataFrame, target: str = "precio_eur_mwh") -> pd.Series:
    """Del DataFrame validado (fecha_hora en hora local) a la serie en UTC que usan los bloques."""
    idx = pd.DatetimeIndex(prices["fecha_hora"]).tz_convert("UTC")
    return pd.Series(prices[target].to_numpy(), index=idx, name=target).sort_index()
