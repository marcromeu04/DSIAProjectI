"""El artefacto que se guarda: modelo + features + metadatos, juntos.

Si se guardara solo el estimador, quien lo cargue tendría que reconstruir las features
igual que en el entrenamiento y acertar con el orden de las columnas. Guardando el
FeatureBuilder dentro, entrenamiento y predicción usan por construcción el mismo cálculo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import pandas as pd

from energia_app.exceptions import ConfigError
from energia_app.features.builder import FeatureBuilder
from energia_app.modeling.evaluation import regression_metrics


@dataclass
class ModelBundle:
    builder: FeatureBuilder
    estimator: object
    timezone: str
    target: str
    trained_until: str
    metadata: dict = field(default_factory=dict)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(self.estimator.predict(X[self.builder.columns]), index=X.index)

    def predict_next_day(self, prices: pd.Series) -> pd.DataFrame:
        """Precio previsto para cada hora del día siguiente al último dato, en hora local."""
        X = self.builder.forecast_table(prices, self.timezone)
        pred = self.predict(X)
        return pd.DataFrame({
            "fecha_hora": X.index.tz_convert(self.timezone),
            "precio_previsto_eur_mwh": pred.round(2).to_numpy(),
        })

    def backtest(self, prices: pd.Series, n_days: int = 7) -> dict:
        """Error real de los últimos n días: cada día se predice solo con los datos anteriores
        y se compara con lo publicado, igual que pasaría en producción."""
        local_days = prices.index.tz_convert(self.timezone).normalize()
        dias = sorted(local_days.unique())[-n_days:]
        filas = []
        for dia in dias:
            historico = prices[local_days < dia]
            real = prices[local_days == dia]
            pred = self.predict(self.builder.forecast_table(historico, self.timezone)).reindex(real.index)
            naive = historico.reindex(real.index - pd.Timedelta(hours=24)).to_numpy()
            filas.append({"dia": str(dia.date()), "horas": int(pred.notna().sum()),
                          "mae_modelo": regression_metrics(real, pred)["mae"],
                          "mae_baseline": regression_metrics(real, naive)["mae"]})
        return {"dias": filas,
                "mae_modelo_media": round(sum(f["mae_modelo"] for f in filas) / len(filas), 2),
                "mae_baseline_media": round(sum(f["mae_baseline"] for f in filas) / len(filas), 2)}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)  # comprimido: unas 4 veces menos espacio en el repo

    @staticmethod
    def load(path: Path) -> "ModelBundle":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"No hay modelo en {path}: ejecuta python -m energia_app.train")
        bundle = joblib.load(path)
        if not isinstance(bundle, ModelBundle):
            raise ConfigError(f"{path} no es un ModelBundle de este proyecto")
        return bundle
