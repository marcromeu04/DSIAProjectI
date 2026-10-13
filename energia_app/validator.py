"""Validación de facturas: separa válidas e inválidas con motivo. Función pura."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from energia_app.exceptions import ValidationError
from energia_app.loader import REQUIRED_COLUMNS

VALID_TARIFFS: frozenset[str] = frozenset({"3.0TD", "6.1TD"})
MIN_POWER_KW = 15  # por debajo de 15 kW no es nuestro cliente


@dataclass(frozen=True)
class ValidationResult:
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
    reasons = pd.Series("", index=frame.index, dtype="object")
    for mask, text in rules:
        mask = mask.fillna(False)
        reasons[mask] = reasons[mask].where(reasons[mask] == "", reasons[mask] + "; ") + text
    return reasons


def validate_invoices(frame: pd.DataFrame) -> ValidationResult:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValidationError(f"Faltan columnas: {missing}")
    work = frame.copy()
    reasons = _reasons(work)
    is_valid = reasons == ""
    valid = work[is_valid].copy()
    for col in ("potencia_contratada_kw", "potencia_maxima_kw", "consumo_kwh",
                "reactiva_kvarh", "importe_total_eur"):
        valid[col] = valid[col].astype(float)
    valid["fecha_inicio"] = pd.to_datetime(valid["fecha_inicio"])
    valid["fecha_fin"] = pd.to_datetime(valid["fecha_fin"])
    invalid = work[~is_valid].copy()
    invalid["motivo"] = reasons[~is_valid]
    return ValidationResult(valid=valid, invalid=invalid)
