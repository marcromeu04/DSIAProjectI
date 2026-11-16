"""Registro de estimadores: del nombre en params.yaml a un Pipeline de sklearn listo para entrenar.

Patrones Registry + Factory, como en las features. Cada estimador se devuelve envuelto en un
Pipeline cuyo último paso se llama "model": así el espacio de búsqueda del YAML (alpha,
max_iter...) se traduce siempre igual a "model__alpha", sea cual sea el modelo (Liskov).
"""

from __future__ import annotations

from typing import Callable

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from energia_app.exceptions import ConfigError

_FACTORIES: dict[str, Callable[[int], Pipeline]] = {}


def register_estimator(name: str):
    """Decorador: la función decorada recibe random_state y devuelve un Pipeline."""

    def decorator(factory: Callable[[int], Pipeline]) -> Callable[[int], Pipeline]:
        if name in _FACTORIES:
            raise ConfigError(f"Ya hay un estimador registrado con el nombre '{name}'")
        _FACTORIES[name] = factory
        return factory

    return decorator


def available_estimators() -> list[str]:
    return sorted(_FACTORIES)


def build_estimator(name: str, random_state: int = 42) -> Pipeline:
    if name not in _FACTORIES:
        raise ConfigError(f"Estimador desconocido: '{name}'. Disponibles: {available_estimators()}")
    return _FACTORIES[name](random_state)


def prefixed(param_space: dict[str, list]) -> dict[str, list]:
    """{"alpha": [...]} → {"model__alpha": [...]}: el YAML no necesita saber que hay un Pipeline."""
    return {f"model__{k}": v for k, v in param_space.items()}


@register_estimator("ridge")
def _ridge(random_state: int) -> Pipeline:
    # Lineal: necesita las features en la misma escala, por eso lleva StandardScaler delante
    return Pipeline([("scale", StandardScaler()), ("model", Ridge())])


@register_estimator("hist_gradient_boosting")
def _hist_gradient_boosting(random_state: int) -> Pipeline:
    # Árboles: no necesitan escalado
    return Pipeline([("model", HistGradientBoostingRegressor(random_state=random_state))])


@register_estimator("random_forest")
def _random_forest(random_state: int) -> Pipeline:
    return Pipeline([("model", RandomForestRegressor(random_state=random_state, n_jobs=-1))])
