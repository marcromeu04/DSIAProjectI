import pytest

from ventas_app.cli import main, run


def test_run_escribe_salidas(sales_csv, tmp_path):
    out = tmp_path / "out" / "limpias.csv"
    summary = run(sales_csv, out)
    assert summary["n_valid"] == 3
    assert out.exists()
    assert (tmp_path / "out" / "limpias_invalidas.csv").exists()


def test_main_devuelve_1_sin_fichero(tmp_path):
    assert main(["--input", str(tmp_path / "nope.csv")]) == 1


@pytest.mark.integration
def test_csv_del_curso_140_validas_10_invalidas(real_sales_csv):
    summary = run(real_sales_csv)
    assert summary["n_valid"] == 140
    assert summary["n_invalid"] == 10
