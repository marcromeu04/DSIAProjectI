"""Contrato común de todos los bloques de features.

Patrón Template Method: transform() es igual para todos los bloques. Comprueba la entrada,
llama a _compute() (lo único que escribe cada bloque) y comprueba la salida. Así ningún
bloque puede devolver un índice desordenado o columnas que no ha declarado, y el resto del
código puede confiar en cualquier bloque sin conocerlo (sustitución de Liskov).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from energia_app.exceptions import FeatureError


class FeatureBlock(ABC):
    """Un grupo de features calculadas a partir de la serie de precios.

    Entrada:
      prices    serie de precios indexada por instante en UTC (el histórico disponible)
      instants  instantes en UTC para los que se quieren features (histórico al entrenar,
                horas de mañana al predecir: el mismo código sirve para las dos cosas)
    Salida: DataFrame con índice = instants y una columna por feature declarada en .columns
    """

    name: str = ""  # lo rellena @register con el nombre que se usa en params.yaml

    @property
    @abstractmethod
    def columns(self) -> list[str]:
        """Nombres de las columnas que produce el bloque."""

    @abstractmethod
    def _compute(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        """El cálculo propio del bloque. Solo se llama a través de transform()."""

    def transform(self, prices: pd.Series, instants: pd.DatetimeIndex) -> pd.DataFrame:
        _check_utc(prices.index, "prices")
        _check_utc(instants, "instants")
        out = self._compute(prices, instants)
        if not out.index.equals(instants):
            raise FeatureError(f"El bloque '{self.name}' ha devuelto un índice distinto del pedido")
        if list(out.columns) != self.columns:
            raise FeatureError(
                f"El bloque '{self.name}' devuelve {list(out.columns)} pero declara {self.columns}"
            )
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, columns={self.columns})"


def _check_utc(index: pd.Index, what: str) -> None:
    if not isinstance(index, pd.DatetimeIndex) or str(index.tz) != "UTC":
        raise FeatureError(f"'{what}' debe estar indexado por fechas en UTC")
    if not index.is_monotonic_increasing:
        raise FeatureError(f"'{what}' debe estar ordenado en el tiempo")
