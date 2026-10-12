"""Validación de ventas: separa válidas e inválidas con motivo. Función pura."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ventas_app.exceptions import ValidationError
from ventas_app.loader import REQUIRED_COLUMNS

VALID_REGIONS: frozenset[str] = frozenset({"Norte", "Sur", "Este", "Oeste"})


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
    units = pd.to_numeric(frame["unidades"], errors="coerce")
    price = pd.to_numeric(frame["precio_unitario"], errors="coerce")
    date = pd.to_datetime(frame["fecha"], errors="coerce")

    rules: list[tuple[pd.Series, str]] = [
        (units.isna(), "unidades no numericas o nulas"),
        (units <= 0, "unidades <= 0"),
        (price.isna(), "precio nulo"),
        (price <= 0, "precio <= 0"),
        (date.isna(), "fecha invalida"),
        (~frame["region"].isin(VALID_REGIONS), "region desconocida"),
        (frame["cliente_id"].isna() | (frame["cliente_id"].astype(str).str.strip() == ""), "cliente vacio"),
    ]
    reasons = pd.Series("", index=frame.index, dtype="object")
    for mask, text in rules:
        mask = mask.fillna(False)
        reasons[mask] = reasons[mask].where(reasons[mask] == "", reasons[mask] + "; ") + text
    return reasons


def validate_sales(frame: pd.DataFrame) -> ValidationResult:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValidationError(f"Faltan columnas: {missing}")
    work = frame.copy()
    reasons = _reasons(work)
    is_valid = reasons == ""
    valid = work[is_valid].copy()
    valid["unidades"] = valid["unidades"].astype(int)
    valid["precio_unitario"] = valid["precio_unitario"].astype(float)
    valid["fecha"] = pd.to_datetime(valid["fecha"])
    invalid = work[~is_valid].copy()
    invalid["motivo"] = reasons[~is_valid]
    return ValidationResult(valid=valid, invalid=invalid)
