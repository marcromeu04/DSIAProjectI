"""Carga de ventas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ventas_app.exceptions import DataLoadError

REQUIRED_COLUMNS: tuple[str, ...] = (
    "fecha", "region", "producto", "unidades", "precio_unitario", "cliente_id",
)


def load_sales(path: Path | str) -> pd.DataFrame:
    """Lee el CSV y comprueba el contrato de columnas."""
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
