import pytest

from ventas_app.exceptions import DataLoadError
from ventas_app.loader import load_sales


def test_lee_csv(sales_csv):
    assert load_sales(sales_csv).shape == (4, 6)


def test_fichero_inexistente(tmp_path):
    with pytest.raises(DataLoadError):
        load_sales(tmp_path / "no_existe.csv")


def test_faltan_columnas(tmp_path):
    path = tmp_path / "mal.csv"
    path.write_text("fecha,region\n2026-01-01,Norte\n")
    with pytest.raises(DataLoadError, match="Faltan columnas"):
        load_sales(path)
