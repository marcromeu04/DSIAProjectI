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


def importe_por_region(validos: pd.DataFrame) -> pd.DataFrame:
    return (
        validos.groupby("region", as_index=False)["importe"].sum()
        .sort_values("importe", ascending=False)
        .reset_index(drop=True)
    )


def top_productos(validos: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return (
        validos.groupby("producto", as_index=False)["importe"].sum()
        .sort_values("importe", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def clientes_recurrentes(validos: pd.DataFrame) -> pd.Series:
    compras = validos["cliente_id"].value_counts()
    return compras[compras > 1]


def exportar(validos: pd.DataFrame, errores: pd.DataFrame, carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    validos.to_csv(carpeta / "ventas_limpias.csv", index=False)
    calidad = {
        "filas_totales": int(len(validos) + len(errores)),
        "filas_validas": int(len(validos)),
        "filas_invalidas": int(len(errores)),
        "importe_total": float(validos["importe"].sum()),
    }
    (carpeta / "calidad_datos.json").write_text(json.dumps(calidad, indent=2), encoding="utf-8")


if __name__ == "__main__":
    frame = pd.read_csv(CSV)
    validos, errores = validar_ventas(frame)
    print(f"válidas: {len(validos)}  inválidas: {len(errores)}")
    print(errores[["unidades", "precio_unitario", "motivo"]])
    print(importe_por_region(validos))
    print(top_productos(validos))
    print(clientes_recurrentes(validos))
    exportar(validos, errores, ROOT / "data")
