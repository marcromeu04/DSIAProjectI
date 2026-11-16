"""Búsqueda automática de hiperparámetros con validación cruzada temporal.

Patrón Strategy: el método de búsqueda (aleatoria o en rejilla) se elige en params.yaml y
ambos se usan con la misma llamada. El resultado de cada candidato es un SearchResult
inmutable con el mejor estimador, sus hiperparámetros, su error en CV y la tabla completa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import BaseCrossValidator, GridSearchCV, RandomizedSearchCV

from energia_app.config import CandidateSpec, SearchConfig
from energia_app.exceptions import ConfigError
from energia_app.modeling.estimators import build_estimator, prefixed

logger = logging.getLogger("energia_app.search")


@dataclass(frozen=True)
class SearchResult:
    name: str
    estimator: object
    best_params: dict
    cv_mae: float
    cv_results: pd.DataFrame


def _searcher(estimator, space: dict, cv: BaseCrossValidator, config: SearchConfig):
    if config.method == "grid":
        return GridSearchCV(estimator, space, cv=cv, scoring=config.scoring, n_jobs=-1, refit=True)
    return RandomizedSearchCV(
        estimator, space, n_iter=config.n_iter, cv=cv, scoring=config.scoring,
        random_state=config.random_state, n_jobs=-1, refit=True,
    )


def search_candidate(candidate: CandidateSpec, X: pd.DataFrame, y: pd.Series,
                     cv: BaseCrossValidator, config: SearchConfig) -> SearchResult:
    """Busca los mejores hiperparámetros de un candidato y lo reentrena con ellos (refit)."""
    if not config.scoring.startswith("neg_"):
        raise ConfigError("search.scoring debe ser una métrica de error negativa de sklearn (neg_...)")
    estimator = build_estimator(candidate.estimator, config.random_state)
    space = prefixed(candidate.param_space)
    combinaciones = 1
    for valores in space.values():
        combinaciones *= len(valores)
    if config.method == "random" and config.n_iter > combinaciones:
        config = SearchConfig("grid", config.n_iter, config.scoring, config.random_state)  # no repetir combinaciones
    searcher = _searcher(estimator, space, cv, config)
    searcher.fit(X, y)
    tabla = pd.DataFrame(searcher.cv_results_)
    tabla.insert(0, "candidate", candidate.name)
    best = {k.removeprefix("model__"): v for k, v in searcher.best_params_.items()}
    cv_mae = round(float(-searcher.best_score_), 3)
    logger.info("candidato=%s mae_cv=%.2f params=%s", candidate.name, cv_mae, best)
    return SearchResult(candidate.name, searcher.best_estimator_, best, cv_mae, tabla)
