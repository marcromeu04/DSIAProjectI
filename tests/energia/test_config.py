import copy
from pathlib import Path

import pytest
import yaml

from energia_app.config import TrainingConfig, load_config, parse_config
from energia_app.exceptions import ConfigError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def raw():
    """El params.yaml real del repo, como diccionario, para romperlo a propósito en cada test."""
    return yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))


def test_el_params_yaml_del_repo_es_valido():
    config = load_config(ROOT / "params.yaml")

    assert isinstance(config, TrainingConfig)
    assert config.data.target == "precio_eur_mwh"
    assert [f.name for f in config.features] == ["calendar", "holidays", "lags", "rolling"]
    assert config.validation.cv_splits == 5
    assert {c.name for c in config.candidates} == {"ridge", "gradient_boosting", "random_forest"}


def test_la_configuracion_es_inmutable(raw):
    config = parse_config(raw)

    with pytest.raises(AttributeError):
        config.validation.test_days = 1


def test_fichero_inexistente(tmp_path):
    with pytest.raises(ConfigError, match="No existe"):
        load_config(tmp_path / "no_existe.yaml")


def test_yaml_mal_formado(tmp_path):
    path = tmp_path / "params.yaml"
    path.write_text("data: [sin cerrar")

    with pytest.raises(ConfigError, match="no es un YAML válido"):
        load_config(path)


def test_yaml_vacio():
    with pytest.raises(ConfigError, match="vacío"):
        parse_config(None)


@pytest.mark.parametrize(
    "romper, mensaje",
    [
        (lambda r: r.pop("data"), "Falta la sección 'data'"),
        (lambda r: r["data"].pop("target"), "Falta 'data.target'"),
        (lambda r: r["validation"].update(cv_splits=1), "cv_splits"),
        (lambda r: r["validation"].update(test_days=-5), "test_days"),
        (lambda r: r["validation"].update(test_days=True), "test_days"),
        (lambda r: r["search"].update(method="bayesiano"), "search.method"),
        (lambda r: r.update(features=[]), "'features' debe ser una lista"),
        (lambda r: r["features"].append({"params": {}}), r"features\[4\] necesita un 'name'"),
        (lambda r: r.update(candidates=[]), "'candidates' debe ser una lista"),
        (lambda r: r["candidates"][0].update(param_space={}), "al menos un hiperparámetro"),
        (lambda r: r["candidates"][0]["param_space"].update(alpha=10), "lista de valores"),
        (lambda r: r["candidates"].append(dict(r["candidates"][0])), "mismo nombre"),
    ],
)
def test_cada_error_dice_que_clave_falla(raw, romper, mensaje):
    roto = copy.deepcopy(raw)
    romper(roto)

    with pytest.raises(ConfigError, match=mensaje):
        parse_config(roto)
