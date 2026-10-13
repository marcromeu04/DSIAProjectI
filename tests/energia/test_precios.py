import pandas as pd
import pytest

from energia_app import metrics
from energia_app.exceptions import ValidationError
from energia_app.validator import validate_prices


@pytest.fixture
def prices_frame():
    # Dos días; hora 20 cara (200) y hora 4 barata (50); el resto a 100
    horas = pd.date_range("2026-03-01", periods=48, freq="h", tz="Europe/Madrid")
    precios = [200.0 if h.hour == 20 else 50.0 if h.hour == 4 else 100.0 for h in horas]
    return pd.DataFrame({
        "fecha_hora": [h.isoformat() for h in horas],
        "precio_eur_mwh": precios,
    })


def test_precios_validos_pasan_todos(prices_frame):
    result = validate_prices(prices_frame)

    assert (result.n_valid, result.n_invalid) == (48, 0)


@pytest.mark.parametrize(
    "valor, motivo",
    [(None, "precio nulo"), (-5.0, "precio <= 0"), (5000.0, "precio fuera de rango")],
)
def test_reglas_de_precio(prices_frame, valor, motivo):
    prices_frame.loc[0, "precio_eur_mwh"] = valor

    result = validate_prices(prices_frame)

    assert result.invalid["motivo"].iloc[0] == motivo


def test_hora_duplicada_se_marca_una_vez(prices_frame):
    con_duplicado = pd.concat([prices_frame, prices_frame.iloc[[3]]], ignore_index=True)

    result = validate_prices(con_duplicado)

    assert result.n_invalid == 1
    assert result.invalid["motivo"].iloc[0] == "hora duplicada"


def test_fecha_invalida(prices_frame):
    prices_frame.loc[0, "fecha_hora"] = "ayer"

    assert validate_prices(prices_frame).invalid["motivo"].iloc[0] == "fecha invalida"


def test_precios_sin_columna(prices_frame):
    with pytest.raises(ValidationError):
        validate_prices(prices_frame.drop(columns=["precio_eur_mwh"]))


def test_precio_por_hora_usa_hora_de_madrid(prices_frame):
    por_hora = metrics.price_by_hour(validate_prices(prices_frame).valid)

    assert len(por_hora) == 24
    assert por_hora.loc[por_hora["hora"] == 20, "precio_eur_mwh"].iloc[0] == 200.0


def test_diferencia_pico_valle(prices_frame):
    valid = validate_prices(prices_frame).valid

    assert metrics.peak_valley_spread(valid) == pytest.approx(150.0)


def test_precio_por_mes(prices_frame):
    por_mes = metrics.price_by_month(validate_prices(prices_frame).valid)

    assert list(por_mes["mes"]) == ["2026-03"]


@pytest.mark.integration
def test_precios_reales_superan_10000_horas(real_prices_csv):
    from energia_app.loader import load_prices

    result = validate_prices(load_prices(real_prices_csv))

    assert result.n_valid >= 10_000
