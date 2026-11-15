import numpy as np
import pandas as pd
import pytest

from energia_app.config import FeatureSpec
from energia_app.exceptions import ConfigError
from energia_app.features import create_block
from energia_app.features.lags import LagFeatures
from tests.energia.features.helpers import assert_sin_futuro, serie_utc


def test_lag_es_el_precio_de_la_misma_hora_antes(serie):
    t = serie.index[24 * 10]

    fila = LagFeatures(hours=[24, 168]).transform(serie, pd.DatetimeIndex([t])).iloc[0]

    assert fila["lag_24h"] == serie[t - pd.Timedelta(hours=24)]
    assert fila["lag_168h"] == serie[t - pd.Timedelta(hours=168)]


def test_sin_historia_suficiente_queda_vacio(serie):
    out = LagFeatures(hours=[168]).transform(serie, serie.index[:200])

    assert out["lag_168h"].isna().sum() == 168


def test_el_dia_del_cambio_de_hora_sigue_siendo_24_horas_reales():
    serie = serie_utc(inicio="2026-03-20", dias=15)
    dia_23h = pd.date_range("2026-03-29", "2026-03-30", freq="h", tz="Europe/Madrid", inclusive="left").tz_convert("UTC")

    out = LagFeatures(hours=[24]).transform(serie, dia_23h)

    assert len(out) == 23
    np.testing.assert_array_equal(out["lag_24h"].to_numpy(), serie.reindex(dia_23h - pd.Timedelta(hours=24)).to_numpy())


@pytest.mark.parametrize("horas", [[1], [12, 24], [], ["24"]])
def test_retardos_menores_que_el_horizonte_se_rechazan(horas):
    with pytest.raises(ConfigError, match="retardo"):
        create_block(FeatureSpec("lags", {"hours": horas}))


def test_no_mira_el_futuro(serie):
    assert_sin_futuro(LagFeatures(hours=[24, 48, 168]), serie, serie.index[24 * 20 + 7])
