import pytest

from energia_app.config import CandidateSpec, SearchConfig, ValidationConfig
from energia_app.exceptions import ConfigError
from energia_app.features.builder import FeatureBuilder
from energia_app.modeling.search import search_candidate
from energia_app.modeling.validation import time_series_cv
from tests.energia.features.helpers import serie_utc
from tests.energia.modeling.helpers import small_config


@pytest.fixture
def tabla():
    config, _ = small_config()
    return FeatureBuilder.from_config(config.features, "Europe/Madrid").training_table(serie_utc())


CV = time_series_cv(ValidationConfig(test_days=7, cv_splits=3, cv_gap_hours=24))


def test_elige_entre_las_combinaciones_y_guarda_la_tabla(tabla):
    X, y = tabla
    cand = CandidateSpec("ridge", "ridge", {"alpha": [0.1, 1000.0]})

    res = search_candidate(cand, X, y, CV, SearchConfig("grid", 5, "neg_mean_absolute_error", 0))

    assert res.best_params["alpha"] in (0.1, 1000.0)
    assert len(res.cv_results) == 2 and res.cv_mae > 0
    assert hasattr(res.estimator, "predict")


def test_random_con_mas_iteraciones_que_combinaciones_no_falla(tabla):
    X, y = tabla
    cand = CandidateSpec("ridge", "ridge", {"alpha": [1.0, 10.0]})

    res = search_candidate(cand, X, y, CV, SearchConfig("random", 50, "neg_mean_absolute_error", 0))

    assert len(res.cv_results) == 2  # se prueban las 2 combinaciones, sin repetir


def test_scoring_que_no_es_un_error_negativo(tabla):
    X, y = tabla
    with pytest.raises(ConfigError, match="neg_"):
        search_candidate(CandidateSpec("ridge", "ridge", {"alpha": [1.0]}), X, y, CV,
                         SearchConfig("grid", 1, "r2", 0))
