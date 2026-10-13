import pandas as pd
import pytest

from energia_app import metrics
from energia_app.validator import validate_invoices


@pytest.fixture
def valid(invoices_frame):
    return validate_invoices(invoices_frame).valid


def test_potencia_optima_con_margen_y_suelo(valid):
    out = metrics.with_savings(valid)

    # F1: maximetro 10 kW * 1.05 = 10.5 -> 11, pero el mínimo es 15
    assert out.loc[out["id_factura"] == "F1", "potencia_optima_kw"].iloc[0] == 15


def test_ahorro_potencia_calculado_a_mano(valid):
    # F1: sobran 30 - 15 = 15 kW durante 30 días a 0.07 EUR/kW/día = 31.5
    # F4: maximetro 18 -> óptima 19, sobra 1 kW * 30 * 0.07 = 2.1
    assert metrics.total_savings(valid) == pytest.approx(31.5 + 2.1)


def test_penalizacion_reactiva_solo_sobre_el_33_por_ciento(valid):
    # F4: 500 - 0.33 * 1000 = 170 kvarh * 0.04 = 6.8, F1 no llega al 33 %
    assert metrics.total_reactive_penalty(valid) == pytest.approx(6.8)


def test_ahorro_por_sector(valid):
    por_sector = metrics.savings_by_sector(valid)

    assert por_sector.iloc[0]["sector"] == "taller"
    assert por_sector["facturas"].sum() == 2


def test_porcentaje_sobredimensionadas(valid):
    assert metrics.oversized_share(valid) == 1.0


def test_porcentaje_sin_facturas(valid):
    assert metrics.oversized_share(valid.iloc[0:0]) == 0.0


def test_precio_medio_pvpc():
    precios = pd.DataFrame({"precio_eur_mwh": [100.0, 200.0, "x"]})

    assert metrics.average_pvpc_price(precios) == 150.0
