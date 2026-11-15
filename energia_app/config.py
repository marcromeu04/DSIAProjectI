"""Configuración del entrenamiento: lee params.yaml y la valida antes de entrenar.

Patrones y principios que se aplican aquí:
- Objeto de configuración tipado (Parameter Object): el resto del código recibe un
  TrainingConfig con atributos con nombre y tipo, no un diccionario donde una clave mal
  escrita solo falla a mitad del entrenamiento.
- Objetos de valor inmutables (frozen dataclasses): nadie puede cambiar la configuración
  después de leerla, así que el modelo guardado y la configuración que lo produjo coinciden.
- Fallo temprano (fail fast): cualquier error del YAML se detecta al arrancar, con un mensaje
  que dice qué clave está mal, antes de gastar minutos entrenando.
- S de SOLID: leer y comprobar la configuración es una responsabilidad distinta de entrenar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from energia_app.exceptions import ConfigError

SEARCH_METHODS = frozenset({"random", "grid"})


@dataclass(frozen=True)
class DataConfig:
    prices_path: Path
    timezone: str
    target: str


@dataclass(frozen=True)
class FeatureSpec:
    """Un bloque de features: su nombre registrado y sus parámetros."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationConfig:
    test_days: int
    cv_splits: int
    cv_gap_hours: int


@dataclass(frozen=True)
class SearchConfig:
    method: str
    n_iter: int
    scoring: str
    random_state: int


@dataclass(frozen=True)
class CandidateSpec:
    """Un modelo candidato: nombre propio, estimador registrado y espacio de búsqueda."""

    name: str
    estimator: str
    param_space: dict[str, list]


@dataclass(frozen=True)
class ArtifactsConfig:
    model_path: Path
    metrics_path: Path
    cv_results_path: Path


@dataclass(frozen=True)
class TrainingConfig:
    data: DataConfig
    features: tuple[FeatureSpec, ...]
    validation: ValidationConfig
    search: SearchConfig
    candidates: tuple[CandidateSpec, ...]
    baselines: tuple[str, ...]
    artifacts: ArtifactsConfig


# --- utilidades de validación: cada una comprueba una cosa y dice dónde está el error ---

def _section(raw: dict, key: str) -> dict:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Falta la sección '{key}' o no es un bloque de claves")
    return value


def _get(section: dict, key: str, where: str) -> Any:
    if key not in section:
        raise ConfigError(f"Falta '{where}.{key}'")
    return section[key]


def _positive_int(section: dict, key: str, where: str, minimum: int = 1) -> int:
    value = _get(section, key, where)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ConfigError(f"'{where}.{key}' debe ser un entero >= {minimum} (tiene {value!r})")
    return value


def _non_empty_list(raw: dict, key: str) -> list:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"'{key}' debe ser una lista con al menos un elemento")
    return value


def _feature(item: Any, i: int) -> FeatureSpec:
    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
        raise ConfigError(f"features[{i}] necesita un 'name' de texto")
    params = item.get("params") or {}
    if not isinstance(params, dict):
        raise ConfigError(f"features[{i}].params debe ser un bloque de claves")
    return FeatureSpec(name=item["name"], params=params)


def _candidate(item: Any, i: int) -> CandidateSpec:
    where = f"candidates[{i}]"
    if not isinstance(item, dict):
        raise ConfigError(f"{where} debe ser un bloque de claves")
    name, estimator = _get(item, "name", where), _get(item, "estimator", where)
    space = _get(item, "param_space", where)
    if not isinstance(space, dict) or not space:
        raise ConfigError(f"{where}.param_space debe tener al menos un hiperparámetro")
    for param, values in space.items():
        if not isinstance(values, list) or not values:
            raise ConfigError(f"{where}.param_space.{param} debe ser una lista de valores a probar")
    return CandidateSpec(name=str(name), estimator=str(estimator), param_space=space)


def parse_config(raw: Any) -> TrainingConfig:
    """Convierte el YAML ya leído en un TrainingConfig, o lanza ConfigError diciendo qué falla."""
    if not isinstance(raw, dict):
        raise ConfigError("params.yaml está vacío o no es un bloque de claves")

    data = _section(raw, "data")
    validation = _section(raw, "validation")
    search = _section(raw, "search")
    artifacts = _section(raw, "artifacts")

    method = _get(search, "method", "search")
    if method not in SEARCH_METHODS:
        raise ConfigError(f"'search.method' debe ser uno de {sorted(SEARCH_METHODS)} (tiene {method!r})")

    candidates = tuple(_candidate(c, i) for i, c in enumerate(_non_empty_list(raw, "candidates")))
    nombres = [c.name for c in candidates]
    if len(set(nombres)) != len(nombres):
        raise ConfigError(f"Hay candidatos con el mismo nombre: {nombres}")

    return TrainingConfig(
        data=DataConfig(
            prices_path=Path(_get(data, "prices_path", "data")),
            timezone=str(_get(data, "timezone", "data")),
            target=str(_get(data, "target", "data")),
        ),
        features=tuple(_feature(f, i) for i, f in enumerate(_non_empty_list(raw, "features"))),
        validation=ValidationConfig(
            test_days=_positive_int(validation, "test_days", "validation"),
            cv_splits=_positive_int(validation, "cv_splits", "validation", minimum=2),
            cv_gap_hours=_positive_int(validation, "cv_gap_hours", "validation", minimum=0),
        ),
        search=SearchConfig(
            method=method,
            n_iter=_positive_int(search, "n_iter", "search"),
            scoring=str(_get(search, "scoring", "search")),
            random_state=int(_get(search, "random_state", "search")),
        ),
        candidates=candidates,
        baselines=tuple(str(b) for b in raw.get("baselines") or ()),
        artifacts=ArtifactsConfig(
            model_path=Path(_get(artifacts, "model_path", "artifacts")),
            metrics_path=Path(_get(artifacts, "metrics_path", "artifacts")),
            cv_results_path=Path(_get(artifacts, "cv_results_path", "artifacts")),
        ),
    )


def load_config(path: Path | str = "params.yaml") -> TrainingConfig:
    """Lee el fichero YAML y lo valida."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"No existe el fichero de configuración: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} no es un YAML válido: {exc}") from exc
    return parse_config(raw)
