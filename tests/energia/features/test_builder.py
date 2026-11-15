from pathlib import Path

import pandas as pd
import pytest

from energia_app.config import FeatureSpec, load_config
from energia_app.exceptions import FeatureError
from energia_app.features import FeatureBlock
from energia_app.features.builder import FeatureBuilder, price_series
from energia_app.features.calendar import CalendarFeatures
from energia_app.features.lags import LagFeatures
from energia_app.loader import load_prices
from energia_app.validator import validate_prices
from tests.energia.features.helpers import assert_sin_futuro, serie_utc

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def builder():
    return FeatureBuilder.from_config(load_config(ROOT / "params.yaml").features, "Europe/Madrid")


def test_crea_los_bloques_de_params_yaml(builder):
    assert [b.name for b in builder.blocks] == ["calendar", "holidays", "lags", "rolling"]
    assert {"hour_sin", "is_holiday", "lag_168h", "roll_std_168h"} <= set(builder.columns)


def test_es_un_bloque_mas_composite(builder, serie):
    out = builder.transform(serie, serie.index[-5:])

    assert isinstance(builder, FeatureBlock)
    assert list(out.columns) == builder.columns


def test_tabla_de_entrenamiento_sin_huecos(builder, serie):
    X, y = builder.training_table(serie)

    assert X.notna().all().all()
    assert X.index.equals(y.index)
    assert len(X) == len(serie) - 168  # se pierde la primera semana: no tiene precio de hace 168 h


def test_prevision_de_mañana_tiene_24_horas(builder, serie):
    tabla = builder.forecast_table(serie, "Europe/Madrid")

    assert len(tabla) == 24
    assert tabla.index.min() > serie.index.max()


def test_el_dia_del_cambio_de_hora_tiene_23_horas(builder):
    # Los datos acaban el sábado 28-03-2026; el domingo 29 se adelanta la hora
    serie = serie_utc(inicio="2026-03-07", dias=22)

    assert len(builder.forecast_table(serie, "Europe/Madrid")) == 23


def test_sin_historia_suficiente_no_predice(builder):
    with pytest.raises(FeatureError, match="historia suficiente"):
        builder.forecast_table(serie_utc(dias=3), "Europe/Madrid")


def test_columnas_repetidas_entre_bloques():
    with pytest.raises(FeatureError, match="mismas columnas"):
        FeatureBuilder([LagFeatures(hours=[24]), LagFeatures(hours=[24, 48])])


def test_ninguna_feature_mira_el_futuro(builder, serie):
    for hora in range(24):
        assert_sin_futuro(builder, serie, serie.index[24 * 20 + hora])


def test_quitar_un_bloque_no_rompe_nada(serie):
    solo_calendario = FeatureBuilder.from_config([FeatureSpec("calendar")], "Europe/Madrid")

    X, _ = solo_calendario.training_table(serie)

    assert list(X.columns) == CalendarFeatures().columns and len(X) == len(serie)


@pytest.mark.integration
def test_con_los_precios_reales(builder, real_prices_csv):
    serie = price_series(validate_prices(load_prices(real_prices_csv)).valid)

    X, y = builder.training_table(serie)
    mañana = builder.forecast_table(serie, "Europe/Madrid")

    assert len(X) > 15_000 and len(mañana) == 24
    assert str(mañana.index.tz_convert("Europe/Madrid")[0].date()) == "2026-10-13"
