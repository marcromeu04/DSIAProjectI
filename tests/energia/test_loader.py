import pytest

from energia_app.exceptions import DataLoadError
from energia_app.loader import load_invoices, load_prices


def test_lee_facturas(invoices_csv):
    assert load_invoices(invoices_csv).shape == (4, 11)


def test_fichero_inexistente(tmp_path):
    with pytest.raises(DataLoadError, match="No existe"):
        load_invoices(tmp_path / "no_existe.csv")


def test_fichero_vacio(tmp_path):
    path = tmp_path / "vacio.csv"
    path.write_text("")
    with pytest.raises(DataLoadError, match="vacío"):
        load_invoices(path)


def test_faltan_columnas(tmp_path):
    path = tmp_path / "mal.csv"
    path.write_text("id_factura,sector\nF1,taller\n")
    with pytest.raises(DataLoadError, match="Faltan columnas"):
        load_invoices(path)


def test_lee_precios(prices_csv):
    assert list(load_prices(prices_csv).columns) == ["fecha_hora", "precio_eur_mwh"]


def test_precios_sin_columna(tmp_path):
    path = tmp_path / "precios_mal.csv"
    path.write_text("fecha_hora\n2026-09-01\n")
    with pytest.raises(DataLoadError, match="Faltan columnas"):
        load_prices(path)
