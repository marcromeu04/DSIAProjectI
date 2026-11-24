import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from energia_app.train import train
from tests.energia.features.helpers import serie_utc
from tests.energia.modeling.helpers import small_config

FACTURA = {
    "id_factura": "F1", "sector": "taller", "tarifa": "3.0TD",
    "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31",
    "potencia_contratada_kw": 30, "potencia_maxima_kw": 10.0,
    "consumo_kwh": 1000, "reactiva_kvarh": 500, "importe_total_eur": 300.0,
}


@pytest.fixture
def rutas(tmp_path):
    """CSV de precios sintéticos y un modelo pequeño entrenado con ellos."""
    serie = serie_utc()
    csv = tmp_path / "precios.csv"
    serie.rename("precio_eur_mwh").rename_axis("fecha_hora").reset_index().assign(
        fecha_hora=lambda d: d["fecha_hora"].map(lambda t: t.isoformat())).to_csv(csv, index=False)
    bundle, _, _ = train(small_config()[0], serie)
    ruta_modelo = tmp_path / "modelo.joblib"
    bundle.save(ruta_modelo)
    return csv, ruta_modelo


@pytest.fixture
def client(rutas, monkeypatch):
    monkeypatch.setenv("AI_MODE", "mock")
    with TestClient(create_app(*rutas)) as c:  # el "with" ejecuta el arranque (lifespan)
        yield c


def test_health_ok(client):
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["price_hours"] == 42 * 24


def test_health_degraded_sin_modelo(rutas, tmp_path):
    with TestClient(create_app(rutas[0], tmp_path / "no_existe.joblib")) as c:
        body = c.get("/health").json()

    assert body["status"] == "degraded" and body["model_loaded"] is False


def test_forecast_sin_modelo_devuelve_503(rutas, tmp_path):
    with TestClient(create_app(rutas[0], tmp_path / "no_existe.joblib")) as c:
        assert c.get("/forecast").status_code == 503


def test_forecast_da_24_horas_y_3_mejores(client):
    body = client.get("/forecast").json()

    assert len(body["horas"]) == 24
    assert len(body["mejores_horas"]) == 3


def test_audit_calcula_ahorro_y_reactiva(client):
    # Mismas cuentas que test_metrics: 15 kW de más * 30 días * 0.07 = 31.5; reactiva 6.8
    body = client.post("/audit", json=FACTURA).json()

    assert body["potencia_optima_kw"] == 15
    assert body["ahorro_potencia_eur"] == pytest.approx(31.5)
    assert body["penalizacion_reactiva_eur"] == pytest.approx(6.8)


def test_audit_factura_invalida_devuelve_422_con_motivo(client):
    respuesta = client.post("/audit", json={**FACTURA, "potencia_contratada_kw": 10})

    assert respuesta.status_code == 422
    assert "15 kW" in respuesta.json()["detail"]


def test_audit_falta_un_campo_devuelve_422(client):
    sin_tarifa = {k: v for k, v in FACTURA.items() if k != "tarifa"}

    assert client.post("/audit", json=sin_tarifa).status_code == 422


def test_explain_en_mock_usa_las_cifras(client):
    body = client.post("/explain", json=FACTURA).json()

    assert body["provider"] == "mock"
    assert "31.50 EUR" in body["text"]


def test_explain_con_hf_sin_token_devuelve_502(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "hf")
    monkeypatch.delenv("HF_TOKEN", raising=False)

    assert client.post("/explain", json=FACTURA).status_code == 502


def test_quality_da_media_de_7_dias(client):
    body = client.get("/quality").json()

    assert len(body["dias"]) == 7
    assert body["mae_modelo_media"] > 0


def test_metrics_cuenta_previsiones_y_peticiones(client):
    client.get("/forecast")
    client.get("/forecast")

    texto = client.get("/metrics").text

    assert "energia_forecast_count_total 2.0" in texto
    assert 'energia_requests_total{endpoint="/forecast",status="200"} 2.0' in texto
    assert "energia_model_mae_7d" in texto
