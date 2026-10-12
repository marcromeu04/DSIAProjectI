"""E1 Partes 2-4: validar, agregar, exportar."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "ventas.csv"


def validar_ventas(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (validos, errores). No modifica la entrada."""
    trabajo = frame.copy()
    unidades = pd.to_numeric(trabajo["unidades"], errors="coerce")
    precio = pd.to_numeric(trabajo["precio_unitario"], errors="coerce")

    motivo = pd.Series("", index=trabajo.index)
    motivo[unidades.isna()] += "unidades no numéricas; "
    motivo[unidades <= 0] += "unidades <= 0; "
    motivo[precio.isna()] += "precio nulo; "
    motivo[precio <= 0] += "precio <= 0; "

    es_valida = motivo == ""
    validos = trabajo[es_valida].copy()
    validos["unidades"] = unidades[es_valida].astype(int)
    validos["precio_unitario"] = precio[es_valida].astype(float)
    validos["importe"] = validos["unidades"] * validos["precio_unitario"]

    errores = trabajo[~es_valida].copy()
    errores["motivo"] = motivo[~es_valida].str.rstrip("; ")
    return validos, errores


if __name__ == "__main__":
    frame = pd.read_csv(CSV)
    validos, errores = validar_ventas(frame)
    print(f"válidas: {len(validos)}  inválidas: {len(errores)}")
    print(errores[["unidades", "precio_unitario", "motivo"]])
