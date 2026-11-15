"""Registro de bloques de features: del nombre en params.yaml a la clase que lo calcula.

Patrones Registry + Factory: cada clase se apunta con @register("nombre") y create_block()
la construye a partir de un FeatureSpec. No hay ningún if/elif por nombre en el código, así
que un bloque nuevo no obliga a modificar este fichero (abierto/cerrado).
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from energia_app.config import FeatureSpec
from energia_app.exceptions import ConfigError
from energia_app.features.base import FeatureBlock

_REGISTRY: dict[str, type[FeatureBlock]] = {}


def register(name: str) -> Callable[[type[FeatureBlock]], type[FeatureBlock]]:
    """Decorador: @register("lags") encima de la clase la hace utilizable desde params.yaml."""

    def decorator(cls: type[FeatureBlock]) -> type[FeatureBlock]:
        if name in _REGISTRY and _REGISTRY[name] is not cls:
            raise ConfigError(f"Ya hay un bloque registrado con el nombre '{name}'")
        if not (isinstance(cls, type) and issubclass(cls, FeatureBlock)):
            raise ConfigError(f"'{name}' debe ser una subclase de FeatureBlock")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorator


def available_blocks() -> list[str]:
    return sorted(_REGISTRY)


def create_block(spec: FeatureSpec, context: dict[str, Any] | None = None) -> FeatureBlock:
    """Construye el bloque que pide la configuración.

    context lleva datos comunes (por ejemplo la zona horaria de params.yaml). Solo se pasan a
    los bloques que los piden en su __init__: inyección de dependencias sin que cada bloque
    tenga que leer la configuración por su cuenta.
    """
    if spec.name not in _REGISTRY:
        raise ConfigError(f"Bloque de features desconocido: '{spec.name}'. Disponibles: {available_blocks()}")
    cls = _REGISTRY[spec.name]
    aceptados = inspect.signature(cls.__init__).parameters
    kwargs = {k: v for k, v in (context or {}).items() if k in aceptados}
    kwargs.update(spec.params)
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise ConfigError(f"Parámetros no válidos para el bloque '{spec.name}': {exc}") from exc
