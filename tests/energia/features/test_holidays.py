import pandas as pd
import pytest

from energia_app.config import FeatureSpec
from energia_app.exceptions import ConfigError
from energia_app.features import create_block
from energia_app.features.holidays import HolidayFeatures


def test_el_12_de_octubre_es_festivo_todo_el_dia_en_hora_local(serie):
    # De 00:00 a 23:00 en Madrid del 12-10-2026 (en UTC empieza el día 11 a las 22:00)
    dia = pd.date_range("2026-10-12", periods=24, freq="h", tz="Europe/Madrid").tz_convert("UTC")

    out = HolidayFeatures().transform(serie, dia)

    assert out["is_holiday"].tolist() == [1] * 24


def test_un_dia_normal_no_es_festivo(serie):
    assert HolidayFeatures().transform(serie, serie.index[24 * 13: 24 * 14])["is_holiday"].sum() == 0


def test_pais_no_soportado():
    with pytest.raises(ConfigError, match="país no soportado"):
        create_block(FeatureSpec("holidays", {"country": "XX"}))
