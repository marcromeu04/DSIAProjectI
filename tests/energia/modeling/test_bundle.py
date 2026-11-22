import pytest

from energia_app.exceptions import ConfigError
from energia_app.features.builder import FeatureBuilder
from energia_app.modeling.bundle import ModelBundle
from energia_app.modeling.estimators import build_estimator
from tests.energia.features.helpers import serie_utc
from tests.energia.modeling.helpers import small_config


@pytest.fixture(scope="module")
def bundle():
    """Un bundle pequeño montado a mano: builder de params.yaml + ridge entrenado."""
    config, _ = small_config()
    builder = FeatureBuilder.from_config(config.features, "Europe/Madrid")
    X, y = builder.training_table(serie_utc())
    return ModelBundle(builder=builder, estimator=build_estimator("ridge").fit(X, y),
                       timezone="Europe/Madrid", target="precio_eur_mwh", trained_until=str(X.index.max()))


def test_predice_las_24_horas_de_mañana(bundle):
    prevision = bundle.predict_next_day(serie_utc())

    assert len(prevision) == 24
    assert str(prevision["fecha_hora"].iloc[0].tz) == "Europe/Madrid"


def test_guardar_y_cargar_da_las_mismas_predicciones(bundle, tmp_path):
    ruta = tmp_path / "modelo.joblib"
    bundle.save(ruta)

    cargado = ModelBundle.load(ruta)

    assert cargado.predict_next_day(serie_utc()).equals(bundle.predict_next_day(serie_utc()))


def test_cargar_sin_modelo(tmp_path):
    with pytest.raises(FileNotFoundError, match="energia_app.train"):
        ModelBundle.load(tmp_path / "no.joblib")


def test_cargar_algo_que_no_es_un_bundle(tmp_path):
    import joblib

    joblib.dump({"no": "soy un bundle"}, tmp_path / "x.joblib")

    with pytest.raises(ConfigError, match="no es un ModelBundle"):
        ModelBundle.load(tmp_path / "x.joblib")


def test_backtest_de_los_ultimos_7_dias(bundle):
    resultado = bundle.backtest(serie_utc(), n_days=7)

    assert len(resultado["dias"]) == 7
    assert all(d["horas"] == 24 for d in resultado["dias"])
    assert resultado["mae_modelo_media"] < resultado["mae_baseline_media"]
