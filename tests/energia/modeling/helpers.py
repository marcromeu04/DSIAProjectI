"""Configuración pequeña para que los tests de modelado tarden segundos, no minutos."""

import copy
from pathlib import Path

import yaml

from energia_app.config import parse_config

ROOT = Path(__file__).resolve().parents[3]


def small_config(tmp_path=None, **cambios):
    raw = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["validation"].update(test_days=7, cv_splits=3, cv_gap_hours=24)
    raw["search"].update(n_iter=2)
    raw["candidates"] = [
        {"name": "ridge", "estimator": "ridge", "param_space": {"alpha": [1.0, 10.0]}},
        {"name": "gradient_boosting", "estimator": "hist_gradient_boosting",
         "param_space": {"max_iter": [30], "learning_rate": [0.1]}},
    ]
    if tmp_path is not None:
        raw["artifacts"] = {"model_path": str(tmp_path / "m.joblib"), "metrics_path": str(tmp_path / "m.json"),
                            "cv_results_path": str(tmp_path / "cv.csv")}
    for clave, valor in cambios.items():
        raw[clave] = valor
    return parse_config(raw), raw
