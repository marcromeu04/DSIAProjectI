import pandas as pd
import pytest

from energia_app.config import ValidationConfig
from energia_app.exceptions import ConfigError
from energia_app.modeling.validation import holdout_split, time_series_cv


@pytest.fixture
def datos():
    idx = pd.date_range("2026-01-01", periods=24 * 40, freq="h", tz="UTC")
    return pd.DataFrame({"x": range(len(idx))}, index=idx), pd.Series(range(len(idx)), index=idx)


def test_el_test_son_los_ultimos_dias(datos):
    X, y = datos

    X_tr, X_te, y_tr, y_te = holdout_split(X, y, test_days=7)

    assert len(X_te) == 24 * 7
    assert X_tr.index.max() < X_te.index.min()


def test_test_days_excesivo(datos):
    with pytest.raises(ConfigError, match="vacío"):
        holdout_split(*datos, test_days=1000)


def test_cada_fold_valida_con_el_futuro_y_respeta_el_hueco(datos):
    X, _ = datos
    cv = time_series_cv(ValidationConfig(test_days=7, cv_splits=4, cv_gap_hours=24))

    folds = list(cv.split(X))

    assert len(folds) == 4
    for train_idx, val_idx in folds:
        assert train_idx.max() + 24 < val_idx.min()  # nunca se entrena con el futuro, y hay 24 h de hueco
