"""KPIs sobre ventas válidas. Funciones puras: DataFrame dentro, DataFrame o número fuera."""

from __future__ import annotations

import pandas as pd


def with_amount(valid: pd.DataFrame) -> pd.DataFrame:
    out = valid.copy()
    out["importe"] = out["unidades"] * out["precio_unitario"]
    return out


def revenue_by_region(valid: pd.DataFrame) -> pd.DataFrame:
    frame = with_amount(valid)
    return (frame.groupby("region", as_index=False)["importe"].sum()
            .sort_values("importe", ascending=False).reset_index(drop=True))


def revenue_by_product(valid: pd.DataFrame) -> pd.DataFrame:
    frame = with_amount(valid)
    return (frame.groupby("producto", as_index=False)
            .agg(unidades=("unidades", "sum"), importe=("importe", "sum"))
            .sort_values("importe", ascending=False).reset_index(drop=True))


def top_clients(valid: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    frame = with_amount(valid)
    return (frame.groupby("cliente_id", as_index=False)["importe"].sum()
            .sort_values("importe", ascending=False).head(n).reset_index(drop=True))


def total_revenue(valid: pd.DataFrame) -> float:
    return float(with_amount(valid)["importe"].sum())
