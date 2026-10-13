"""Métricas de ahorro (facturas) y de precio (PVPC).

Funciones puras: DataFrame dentro, DataFrame o número fuera. Todas las cuentas
son deterministas y se pueden comprobar a mano; aquí no interviene ningún modelo.
"""

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
    out = valid.copy()  # no modificamos el DataFrame que nos pasan
    # Potencia óptima: lo que de verdad se usó (maxímetro) más un 5 % de margen
    optima = (out["potencia_maxima_kw"] * MARGEN_POTENCIA).apply(math.ceil)
    out["potencia_optima_kw"] = optima.clip(lower=MIN_POWER_KW)

    # Lo que sobra de potencia se paga cada día del periodo
    dias = (out["fecha_fin"] - out["fecha_inicio"]).dt.days
    sobra = (out["potencia_contratada_kw"] - out["potencia_optima_kw"]).clip(lower=0)
    out["ahorro_potencia_eur"] = sobra * dias * EUR_KW_DIA

    # Solo se paga la reactiva que supera el 33 % de la energía activa
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
    """Facturas, ahorro y penalización por sector, de mayor a menor ahorro."""
    frame = with_savings(valid)
    return (frame.groupby("sector", as_index=False)
            .agg(facturas=("id_factura", "count"),
                 ahorro_potencia_eur=("ahorro_potencia_eur", "sum"),
                 penalizacion_reactiva_eur=("penalizacion_reactiva_eur", "sum"))
            .sort_values("ahorro_potencia_eur", ascending=False).reset_index(drop=True))


def oversized_share(valid: pd.DataFrame) -> float:
    """Fracción de facturas con potencia contratada por encima de la óptima."""
    if valid.empty:  # evita dividir entre cero si no hay facturas
        return 0.0
    frame = with_savings(valid)
    return float((frame["ahorro_potencia_eur"] > 0).mean())


def average_pvpc_price(prices: pd.DataFrame) -> float:
    """Precio medio PVPC del periodo descargado (EUR/MWh)."""
    # coerce: si llega algún valor no numérico, se ignora en la media
    return float(pd.to_numeric(prices["precio_eur_mwh"], errors="coerce").mean())


def price_by_hour(prices: pd.DataFrame) -> pd.DataFrame:
    """Precio medio por hora del día (0-23), sobre precios ya validados."""
    # fecha_hora ya viene en hora de Madrid desde validate_prices
    hora = prices["fecha_hora"].dt.hour.rename("hora")
    return (prices.groupby(hora)["precio_eur_mwh"].mean()
            .reset_index().sort_values("hora").reset_index(drop=True))


def price_by_month(prices: pd.DataFrame) -> pd.DataFrame:
    """Precio medio por mes (AAAA-MM)."""
    mes = prices["fecha_hora"].dt.strftime("%Y-%m").rename("mes")
    return prices.groupby(mes)["precio_eur_mwh"].mean().reset_index()


def peak_valley_spread(prices: pd.DataFrame) -> float:
    """Diferencia entre la hora media más cara y la más barata (EUR/MWh).

    Es lo que se ahorra, de media, moviendo 1 MWh de la peor hora a la mejor.
    """
    por_hora = price_by_hour(prices)["precio_eur_mwh"]
    return float(por_hora.max() - por_hora.min())
