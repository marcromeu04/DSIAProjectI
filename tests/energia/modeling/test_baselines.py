import numpy as np
import pandas as pd
import pytest

from energia_app.exceptions import ConfigError
from energia_app.modeling.baselines import NaiveLag, build_baseline
from energia_app.modeling.evaluation import regression_metrics


def test_naive_devuelve_la_columna_del_retardo():
    X = pd.DataFrame({"lag_24h": [10.0, 20.0], "lag_168h": [1.0, 2.0]})

    assert build_baseline("naive_24h").fit(X).predict(X).tolist() == [10.0, 20.0]
    assert build_baseline("naive_168h").fit(X).predict(X).tolist() == [1.0, 2.0]


def test_sin_la_feature_necesaria_falla_con_mensaje_claro():
    with pytest.raises(ConfigError, match="lag_168h"):
        NaiveLag(168).fit(pd.DataFrame({"lag_24h": [1.0]}))


def test_baseline_desconocido():
    with pytest.raises(ConfigError, match="Disponibles"):
        build_baseline("naive_1h")


def test_metricas_calculadas_a_mano():
    m = regression_metrics([100, 100, 100], [90, 110, 130])

    assert m["mae"] == pytest.approx((10 + 10 + 30) / 3, abs=1e-3)
    assert m["rmse"] == pytest.approx(np.sqrt((100 + 100 + 900) / 3), abs=1e-3)
    assert m["bias"] == pytest.approx(10.0)  # de media se pasa 10 EUR/MWh
