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


def _modelo_pequeño(tmp_path):
    """Entrena un modelo de prueba con precios sintéticos y lo guarda; devuelve (csv, modelo)."""
    from energia_app.train import train
    from tests.energia.features.helpers import serie_utc
    from tests.energia.modeling.helpers import small_config

    serie = serie_utc()
    csv = tmp_path / "precios.csv"
    serie.rename("precio_eur_mwh").rename_axis("fecha_hora").reset_index().assign(
        fecha_hora=lambda d: d["fecha_hora"].map(lambda t: t.isoformat())).to_csv(csv, index=False)
    bundle, _, _ = train(small_config()[0], serie)
    ruta = tmp_path / "modelo.joblib"
    bundle.save(ruta)
    return csv, ruta


def test_main_con_modelo_muestra_las_mejores_horas(tmp_path, invoices_csv, capsys):
    csv, modelo = _modelo_pequeño(tmp_path)

    codigo = main(["--input", str(invoices_csv), "--prices", str(csv), "--model", str(modelo)])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "Prevision para" in salida and "Mejores horas para consumir" in salida


def test_main_con_modelo_inexistente_devuelve_1(invoices_csv, prices_csv, tmp_path):
    assert main(["--input", str(invoices_csv), "--prices", str(prices_csv),
                 "--model", str(tmp_path / "nada.joblib")]) == 1
