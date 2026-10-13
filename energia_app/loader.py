"""Carga de facturas de luz."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from energia_app.exceptions import DataLoadError

REQUIRED_COLUMNS: tuple[str, ...] = (
    "id_factura", "sector", "provincia", "tarifa", "fecha_inicio", "fecha_fin",
    "potencia_contratada_kw", "potencia_maxima_kw", "consumo_kwh",
    "reactiva_kvarh", "importe_total_eur",
)


def load_invoices(path: Path | str) -> pd.DataFrame:
    """Lee el CSV y comprueba que están todas las columnas."""
    path = Path(path)
    if not path.exists():
        raise DataLoadError(f"No existe el fichero: {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"Fichero vacío: {path}") from exc
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise DataLoadError(f"Faltan columnas obligatorias: {missing}")
    return frame



PRICE_COLUMNS: tuple[str, ...] = ("fecha_hora", "precio_eur_mwh")


def load_prices(path: Path | str) -> pd.DataFrame:
    """Lee el CSV de precios PVPC descargado de REData."""
    path = Path(path)
    if not path.exists():
        raise DataLoadError(f"No existe el fichero: {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"Fichero vacío: {path}") from exc
    missing = [c for c in PRICE_COLUMNS if c not in frame.columns]
    if missing:
        raise DataLoadError(f"Faltan columnas obligatorias: {missing}")
    return frame
