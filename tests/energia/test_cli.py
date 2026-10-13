import pytest

from energia_app.cli import main, run


def test_run_resume_validas_e_invalidas(invoices_csv):
    resumen = run(invoices_csv)

    assert resumen["n_valid"] == 2
    assert resumen["n_invalid"] == 2
    assert resumen["pvpc_avg"] is None


def test_run_con_precios_y_salida(invoices_csv, prices_csv, tmp_path):
    salida = tmp_path / "out" / "validas.csv"

    resumen = run(invoices_csv, prices_csv, salida)

    assert resumen["pvpc_avg"] == 150.0
    assert salida.exists()
    assert (tmp_path / "out" / "validas_invalidas.csv").exists()


def test_main_devuelve_1_si_no_existe(tmp_path):
    assert main(["--input", str(tmp_path / "nada.csv")]) == 1


def test_main_devuelve_0_y_escribe_informe(invoices_csv, capsys):
    codigo = main(["--input", str(invoices_csv)])

    assert codigo == 0
    assert "Validas: 2  Invalidas: 2" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_completo_sobre_datos_reales(real_invoices_csv):
    resumen = run(real_invoices_csv)

    assert resumen["n_valid"] == 9000
    assert resumen["total_savings"] > 0


def test_main_con_precios_muestra_horas_caras(invoices_csv, prices_csv, capsys):
    codigo = main(["--input", str(invoices_csv), "--prices", str(prices_csv)])

    assert codigo == 0
    assert "Horas mas caras" in capsys.readouterr().out
