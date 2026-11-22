"""Entrenamiento de principio a fin: python -m energia_app.train [--params params.yaml]

Patrón Facade: un único punto de entrada que esconde las piezas (configuración, features,
validación, búsqueda, evaluación, artefacto). Cada pieza se recibe ya construida a partir de
la configuración (inyección de dependencias), así que esta función no conoce ninguna feature
ni ningún modelo concreto.

Pasos:
 1. Precios validados → serie en UTC → tabla de features (FeatureBuilder).
 2. Se reservan los últimos días como test.
 3. Cada candidato busca sus hiperparámetros con validación cruzada temporal.
 4. Gana el de menor error en CV (nunca se mira el test para elegir).
 5. El ganador y los baselines se evalúan una sola vez en el test.
 6. El ganador se reentrena con todos los datos y se guarda junto a sus features.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from energia_app.config import TrainingConfig, load_config
from energia_app.exceptions import ConfigError, DataLoadError, FeatureError, ValidationError
from energia_app.features.builder import FeatureBuilder, price_series
from energia_app.loader import load_prices
from energia_app.modeling.baselines import build_baseline
from energia_app.modeling.bundle import ModelBundle
from energia_app.modeling.evaluation import regression_metrics
from energia_app.modeling.search import search_candidate
from energia_app.modeling.validation import holdout_split, time_series_cv
from energia_app.validator import validate_prices

logger = logging.getLogger("energia_app.train")


def train(config: TrainingConfig, prices: pd.Series) -> tuple[ModelBundle, dict, pd.DataFrame]:
    """Entrena con una serie de precios ya preparada. Sin ficheros: se puede probar en memoria."""
    builder = FeatureBuilder.from_config(config.features, config.data.timezone)
    X, y = builder.training_table(prices)
    X_train, X_test, y_train, y_test = holdout_split(X, y, config.validation.test_days)
    cv = time_series_cv(config.validation)
    logger.info("horas entreno=%d test=%d features=%d", len(X_train), len(X_test), X.shape[1])

    resultados = [search_candidate(c, X_train, y_train, cv, config.search) for c in config.candidates]
    ganador = min(resultados, key=lambda r: r.cv_mae)

    test = {"modelo": regression_metrics(y_test, ganador.estimator.predict(X_test))}
    for nombre in config.baselines:
        base = build_baseline(nombre).fit(X_train, y_train)
        test[nombre] = regression_metrics(y_test, base.predict(X_test))

    final = clone(ganador.estimator).fit(X, y)  # mismo modelo y parámetros, con todos los datos
    metricas = {
        "ganador": ganador.name,
        "hiperparametros": ganador.best_params,
        "cv_mae_por_candidato": {r.name: r.cv_mae for r in resultados},
        "test": test,
        "horas_entreno": len(X_train),
        "horas_test": len(X_test),
        "features": builder.columns,
        "entrenado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if config.baselines:
        mejor_base = min(test[b]["mae"] for b in config.baselines)
        metricas["mejora_mae_vs_mejor_baseline_pct"] = round(100 * (1 - test["modelo"]["mae"] / mejor_base), 1)
    bundle = ModelBundle(builder=builder, estimator=final, timezone=config.data.timezone,
                         target=config.data.target, trained_until=str(prices.index.max()), metadata=metricas)
    return bundle, metricas, pd.concat([r.cv_results for r in resultados], ignore_index=True)


def main(argv: list[str] | None = None) -> int:
    """0 si entrena y guarda; 1 si la configuración o los datos no sirven."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Entrena el modelo de precio")
    parser.add_argument("--params", type=Path, default=Path("params.yaml"))
    args = parser.parse_args(argv)
    try:
        config = load_config(args.params)
        prices = price_series(validate_prices(load_prices(config.data.prices_path)).valid, config.data.target)
        bundle, metricas, cv_results = train(config, prices)
    except (ConfigError, DataLoadError, ValidationError, FeatureError) as exc:
        logger.error("%s", exc)
        return 1

    bundle.save(config.artifacts.model_path)
    config.artifacts.metrics_path.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    cv_results.to_csv(config.artifacts.cv_results_path, index=False)

    print(f"Ganador: {metricas['ganador']} {metricas['hiperparametros']}")
    print("MAE en validación cruzada por candidato:", metricas["cv_mae_por_candidato"])
    for nombre, m in metricas["test"].items():
        print(f"MAE en test  {nombre:<12} {m['mae']:7.2f} EUR/MWh")
    if "mejora_mae_vs_mejor_baseline_pct" in metricas:
        print(f"Mejora frente al mejor baseline: {metricas['mejora_mae_vs_mejor_baseline_pct']} %")
    print(f"Modelo guardado en {config.artifacts.model_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
