import pandas as pd
import pytest

from energia_app.config import FeatureSpec
from energia_app.exceptions import ConfigError
from energia_app.features import create_block
from energia_app.features.rolling import RollingFeatures
from tests.energia.features.helpers import assert_sin_futuro


def test_media_de_la_ventana_que_acaba_24h_antes(serie):
    t = serie.index[24 * 15]
    fin = t - pd.Timedelta(hours=24)
    esperada = serie[(serie.index > fin - pd.Timedelta(hours=24)) & (serie.index <= fin)].mean()

    fila = RollingFeatures(windows_hours=[24]).transform(serie, pd.DatetimeIndex([t])).iloc[0]

    assert fila["roll_mean_24h"] == pytest.approx(esperada)


def test_columnas_por_ventana_y_estadistico():
    bloque = RollingFeatures(windows_hours=[168, 24], stats=["mean", "max"])

    assert bloque.columns == ["roll_mean_24h", "roll_max_24h", "roll_mean_168h", "roll_max_168h"]


@pytest.mark.parametrize(
    "params, mensaje",
    [
        ({"windows_hours": [24], "shift_hours": 1}, "shift_hours"),
        ({"windows_hours": []}, "ventana"),
        ({"windows_hours": [24], "stats": ["mediana"]}, "stats"),
    ],
)
def test_parametros_no_validos(params, mensaje):
    with pytest.raises(ConfigError, match=mensaje):
        create_block(FeatureSpec("rolling", params))


def test_no_mira_el_futuro(serie):
    assert_sin_futuro(RollingFeatures(windows_hours=[24, 168]), serie, serie.index[24 * 20 + 13])
