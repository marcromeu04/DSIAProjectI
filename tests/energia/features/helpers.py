"""Utilidades compartidas por los tests de features."""

import numpy as np
import pandas as pd


def serie_utc(inicio="2026-01-01", dias=42, tz="Europe/Madrid", semilla=0) -> pd.Series:
    """Precios horarios sintéticos con patrón diario y fines de semana más baratos, indexados en UTC."""
    horas = pd.date_range(inicio, periods=24 * dias, freq="h", tz=tz)
    rng = np.random.default_rng(semilla)
    valores = 100 + 60 * np.sin((horas.hour - 6) / 24 * 2 * np.pi) + np.where(horas.dayofweek >= 5, -40, 0)
    return pd.Series(valores + rng.normal(0, 3, len(horas)), index=horas.tz_convert("UTC"), name="precio_eur_mwh")


def assert_sin_futuro(bloque, serie, instante, horizonte_horas=24):
    """Cambia todos los precios posteriores al corte (instante - horizonte) y comprueba que las
    features de ese instante no cambian: el bloque solo usa lo que ya se sabía."""
    corte = instante - pd.Timedelta(hours=horizonte_horas)
    alterada = serie.copy()
    alterada[alterada.index > corte] += 1000
    idx = pd.DatetimeIndex([instante])
    pd.testing.assert_frame_equal(bloque.transform(serie, idx), bloque.transform(alterada, idx))
