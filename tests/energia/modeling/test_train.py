import json

import pytest
import yaml

from energia_app import train as train_mod
from energia_app.train import train
from tests.energia.features.helpers import serie_utc
from tests.energia.modeling.helpers import small_config


def test_elige_por_cv_y_evalua_contra_los_baselines():
    config, _ = small_config()

    bundle, metricas, cv = train(config, serie_utc())

    assert metricas["ganador"] == min(metricas["cv_mae_por_candidato"], key=metricas["cv_mae_por_candidato"].get)
    assert set(metricas["test"]) == {"modelo", "naive_24h", "naive_168h"}
    assert metricas["test"]["modelo"]["mae"] < metricas["test"]["naive_24h"]["mae"]
    assert set(cv["candidate"]) == {"ridge", "gradient_boosting"}
    assert bundle.metadata == metricas


def test_main_guarda_modelo_metricas_y_tabla_de_cv(tmp_path, monkeypatch):
    config, raw = small_config(tmp_path)
    csv = tmp_path / "precios.csv"
    s = serie_utc()
    s.rename("precio_eur_mwh").rename_axis("fecha_hora").reset_index().assign(
        fecha_hora=lambda d: d["fecha_hora"].map(lambda t: t.isoformat())).to_csv(csv, index=False)
    raw["data"]["prices_path"] = str(csv)
    params = tmp_path / "params.yaml"
    params.write_text(yaml.safe_dump(raw))

    assert train_mod.main(["--params", str(params)]) == 0
    assert (tmp_path / "m.joblib").exists() and (tmp_path / "cv.csv").exists()
    assert json.loads((tmp_path / "m.json").read_text())["ganador"] in {"ridge", "gradient_boosting"}


def test_main_con_configuracion_rota_devuelve_1(tmp_path):
    params = tmp_path / "params.yaml"
    params.write_text("data: {}\n")

    assert train_mod.main(["--params", str(params)]) == 1


def test_main_con_estimador_desconocido_devuelve_1(tmp_path):
    _, raw = small_config(tmp_path)
    raw["candidates"][0]["estimator"] = "no_existe"
    params = tmp_path / "params.yaml"
    params.write_text(yaml.safe_dump(raw))

    assert train_mod.main(["--params", str(params)]) == 1


@pytest.mark.integration
def test_con_los_precios_reales_gana_a_los_baselines(real_prices_csv):
    from energia_app.features.builder import price_series
    from energia_app.loader import load_prices
    from energia_app.validator import validate_prices

    from energia_app.config import parse_config

    _, raw = small_config()
    raw["validation"]["test_days"] = 30  # los 7 últimos días incluyen el festivo del 12 de octubre
    _, metricas, _ = train(parse_config(raw), price_series(validate_prices(load_prices(real_prices_csv)).valid))

    assert metricas["mejora_mae_vs_mejor_baseline_pct"] > 0
