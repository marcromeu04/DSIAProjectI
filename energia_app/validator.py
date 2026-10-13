"""Validación de facturas y precios: separa filas válidas e inválidas con su motivo.

Las funciones de este módulo son puras: reciben un DataFrame y devuelven otro,
sin leer ni escribir disco. Por eso se pueden testear con unas pocas filas.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from energia_app.exceptions import ValidationError
from energia_app.loader import PRICE_COLUMNS, REQUIRED_COLUMNS

VALID_TARIFFS: frozenset[str] = frozenset({"3.0TD", "6.1TD"})
MIN_POWER_KW = 15  # por debajo de 15 kW no es nuestro cliente


@dataclass(frozen=True)
class ValidationResult:
    """Resultado de validar: filas buenas y filas malas (con columna `motivo`).

    Es inmutable (frozen) para que nadie lo modifique por error después de validar.
    """

    valid: pd.DataFrame
    invalid: pd.DataFrame

    @property
    def n_valid(self) -> int:
        return len(self.valid)

    @property
    def n_invalid(self) -> int:
        return len(self.invalid)


def _reasons(frame: pd.DataFrame) -> pd.Series:
    """Motivo por fila; cadena vacía si la fila es válida."""
    # errors="coerce" convierte lo que no es número/fecha en NaN/NaT,
    # así una sola regla isna() detecta tanto huecos como basura
    contratada = pd.to_numeric(frame["potencia_contratada_kw"], errors="coerce")
    maximetro = pd.to_numeric(frame["potencia_maxima_kw"], errors="coerce")
    consumo = pd.to_numeric(frame["consumo_kwh"], errors="coerce")
    reactiva = pd.to_numeric(frame["reactiva_kvarh"], errors="coerce")
    importe = pd.to_numeric(frame["importe_total_eur"], errors="coerce")
    inicio = pd.to_datetime(frame["fecha_inicio"], errors="coerce")
    fin = pd.to_datetime(frame["fecha_fin"], errors="coerce")

    rules: list[tuple[pd.Series, str]] = [
        (contratada.isna() | (contratada < MIN_POWER_KW), "potencia contratada < 15 kW o nula"),
        (maximetro.isna() | (maximetro < 0), "maximetro negativo o nulo"),
        (consumo.isna() | (consumo < 0), "consumo negativo o nulo"),
        (reactiva.isna() | (reactiva < 0), "reactiva negativa o nula"),
        (importe.isna() | (importe <= 0), "importe nulo o <= 0"),
        (inicio.isna() | fin.isna(), "fecha invalida"),
        (fin <= inicio, "periodo sin dias"),
        (~frame["tarifa"].isin(VALID_TARIFFS), "tarifa desconocida"),
    ]
    # Una fila puede romper varias reglas: se concatenan todos sus motivos
    reasons = pd.Series("", index=frame.index, dtype="object")
    for mask, text in rules:
        mask = mask.fillna(False)
        reasons[mask] = reasons[mask].where(reasons[mask] == "", reasons[mask] + "; ") + text
    return reasons


def validate_invoices(frame: pd.DataFrame) -> ValidationResult:
    """Aplica las reglas de facturas y devuelve válidas (ya tipadas) e inválidas."""
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValidationError(f"Faltan columnas: {missing}")
    work = frame.copy()
    reasons = _reasons(work)
    is_valid = reasons == ""
    valid = work[is_valid].copy()
    # Las válidas salen con tipos limpios para que metrics no tenga que convertir nada
    for col in ("potencia_contratada_kw", "potencia_maxima_kw", "consumo_kwh",
                "reactiva_kvarh", "importe_total_eur"):
        valid[col] = valid[col].astype(float)
    valid["fecha_inicio"] = pd.to_datetime(valid["fecha_inicio"])
    valid["fecha_fin"] = pd.to_datetime(valid["fecha_fin"])
    invalid = work[~is_valid].copy()
    invalid["motivo"] = reasons[~is_valid]
    return ValidationResult(valid=valid, invalid=invalid)


# Rango plausible del precio. Puede ser negativo: con mucha solar a mediodía
# el mercado llega a pagar por consumir. Fuera de este rango, error de la fuente.
MIN_PRICE_EUR_MWH = -500
MAX_PRICE_EUR_MWH = 1000


def _price_reasons(frame: pd.DataFrame) -> pd.Series:
    """Motivo por hora de precio; cadena vacía si la fila es válida."""
    fecha = pd.to_datetime(frame["fecha_hora"], format="ISO8601", utc=True, errors="coerce")
    precio = pd.to_numeric(frame["precio_eur_mwh"], errors="coerce")

    rules: list[tuple[pd.Series, str]] = [
        (fecha.isna(), "fecha invalida"),
        # Se compara en UTC: en el cambio de hora de octubre las 02:00 locales
        # se repiten, pero en UTC son dos horas distintas y ambas son reales
        (fecha.duplicated(keep="first") & fecha.notna(), "hora duplicada"),
        (precio.isna(), "precio nulo"),
        ((precio < MIN_PRICE_EUR_MWH) | (precio > MAX_PRICE_EUR_MWH), "precio fuera de rango"),
    ]
    # Mismo mecanismo que en facturas: un motivo por regla incumplida
    reasons = pd.Series("", index=frame.index, dtype="object")
    for mask, text in rules:
        mask = mask.fillna(False)
        reasons[mask] = reasons[mask].where(reasons[mask] == "", reasons[mask] + "; ") + text
    return reasons


def validate_prices(frame: pd.DataFrame) -> ValidationResult:
    """Aplica las reglas de precios horarios y devuelve válidos en hora de Madrid."""
    missing = [c for c in PRICE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValidationError(f"Faltan columnas: {missing}")
    work = frame.copy()
    reasons = _price_reasons(work)
    is_valid = reasons == ""
    valid = work[is_valid].copy()
    # Pasamos a hora de Madrid para que las 20:00 sean las 20:00 de verdad
    valid["fecha_hora"] = pd.to_datetime(valid["fecha_hora"], utc=True).dt.tz_convert("Europe/Madrid")
    valid["precio_eur_mwh"] = valid["precio_eur_mwh"].astype(float)
    invalid = work[~is_valid].copy()
    invalid["motivo"] = reasons[~is_valid]
    return ValidationResult(valid=valid, invalid=invalid)
