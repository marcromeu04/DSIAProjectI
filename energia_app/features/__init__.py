"""Features del modelo de precio, organizadas en bloques independientes.

Cada módulo de esta carpeta define uno o varios bloques y los registra con @register.
Aquí se importan todos automáticamente: añadir un bloque nuevo es crear un fichero en
esta carpeta, sin editar este ni ningún otro (principio abierto/cerrado).
"""

import importlib
import pkgutil

from energia_app.features.base import FeatureBlock
from energia_app.features.registry import available_blocks, create_block, register

# Importa cada módulo de la carpeta para que sus @register se ejecuten
for _modulo in pkgutil.iter_modules(__path__):
    if _modulo.name not in {"base", "registry"}:
        importlib.import_module(f"{__name__}.{_modulo.name}")

__all__ = ["FeatureBlock", "available_blocks", "create_block", "register"]
