"""KPIs sobre facturas válidas. Funciones puras: DataFrame dentro, DataFrame o número fuera."""

from __future__ import annotations

import math

import pandas as pd

# Mismos precios inventados que usa el generador de facturas
EUR_KW_DIA = 0.07
EUR_KVARH = 0.04
REACTIVA_LIMITE = 0.33  # la reactiva se penaliza por encima del 33 % del consumo
MARGEN_POTENCIA = 1.05  # dejamos un 5 % de margen sobre el maximetro
MIN_POWER_KW = 15


def with_savings(valid: pd.DataFrame) -> pd.DataFrame:
    """Añade potencia óptima, ahorro por potencia y penalización por reactiva."""
    out = valid.copy()
    optima = (out["potencia_maxima_kw"] * MARGEN_POTENCIA).apply(math.ceil)
    out["potencia_optima_kw"] = optima.clip(lower=MIN_POWER_KW)

    dias = (out["fecha_fin"] - out["fecha_inicio"]).dt.days
    sobra = (out["potencia_contratada_kw"] - out["potencia_optima_kw"]).clip(lower=0)
    out["ahorro_potencia_eur"] = sobra * dias * EUR_KW_DIA

    exceso = (out["reactiva_kvarh"] - REACTIVA_LIMITE * out["consumo_kwh"]).clip(lower=0)
    out["penalizacion_reactiva_eur"] = exceso * EUR_KVARH
    return out


def total_savings(valid: pd.DataFrame) -> float:
    """Ahorro potencial total por ajustar potencia (en euros)."""
    return float(with_savings(valid)["ahorro_potencia_eur"].sum())


def total_reactive_penalty(valid: pd.DataFrame) -> float:
    """Euros pagados de más por energía reactiva."""
    return float(with_savings(valid)["penalizacion_reactiva_eur"].sum())


def savings_by_sector(valid: pd.DataFrame) -> pd.DataFrame:
    frame = with_savings(valid)
    return (frame.groupby("sector", as_index=False)
            .agg(facturas=("id_factura", "count"),
                 ahorro_potencia_eur=("ahorro_potencia_eur", "sum"),
                 penalizacion_reactiva_eur=("penalizacion_reactiva_eur", "sum"))
            .sort_values("ahorro_potencia_eur", ascending=False).reset_index(drop=True))


def oversized_share(valid: pd.DataFrame) -> float:
    """Fracción de facturas con potencia contratada por encima de la óptima."""
    if valid.empty:
        return 0.0
    frame = with_savings(valid)
    return float((frame["ahorro_potencia_eur"] > 0).mean())


def average_pvpc_price(prices: pd.DataFrame) -> float:
    """Precio medio PVPC del periodo descargado (EUR/MWh)."""
    return float(pd.to_numeric(prices["precio_eur_mwh"], errors="coerce").mean())
