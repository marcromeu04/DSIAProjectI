"""Errores con nombre del pipeline de facturas de luz."""


class DataLoadError(Exception):
    """No se ha podido cargar la entrada (no existe, vacía o sin columnas)."""


class ValidationError(Exception):
    """La entrada no cumple el contrato de columnas."""
