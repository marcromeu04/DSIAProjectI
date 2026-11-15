import numpy as np
import pandas as pd
import pytest

from energia_app.config import FeatureSpec
from energia_app.features import create_block
from energia_app.features.calendar import CalendarFeatures


def test_usa_la_hora_local_no_la_utc(serie):
    # 2026-01-03 23:00 UTC son las 00:00 del domingo 4 en Madrid
    instante = pd.DatetimeIndex([pd.Timestamp("2026-01-03 23:00", tz="UTC")])

    fila = CalendarFeatures().transform(serie, instante).iloc[0]

    assert (fila["hour"], fila["dow"], fila["is_weekend"]) == (0, 6, 1)


def test_las_23_y_las_0_quedan_juntas_en_el_ciclo(serie):
    instantes = pd.DatetimeIndex(pd.to_datetime(["2026-01-05 22:00", "2026-01-05 23:00"], utc=True))

    t = CalendarFeatures().transform(serie, instantes)
    a, b = t[["hour_sin", "hour_cos"]].to_numpy()

    assert np.linalg.norm(a - b) < 0.3  # 23:00 y 00:00 locales, casi el mismo punto del círculo


def test_columnas_segun_parametros(serie):
    solo_enteros = CalendarFeatures(cyclical=False)

    assert solo_enteros.columns == ["hour", "dow", "month", "is_weekend"]
    assert list(solo_enteros.transform(serie, serie.index[:3]).columns) == solo_enteros.columns


def test_desactivar_todo_es_un_error_de_configuracion():
    from energia_app.exceptions import ConfigError

    with pytest.raises(ConfigError):
        create_block(FeatureSpec("calendar", {"cyclical": False, "integers": False}))


def test_no_depende_del_precio(serie):
    # Mismas fechas, precios distintos: las features de calendario no cambian
    otro = serie * 3 + 50

    pd.testing.assert_frame_equal(
        CalendarFeatures().transform(serie, serie.index), CalendarFeatures().transform(otro, otro.index)
    )
