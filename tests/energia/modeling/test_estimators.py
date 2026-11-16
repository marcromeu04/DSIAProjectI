import pytest
from sklearn.pipeline import Pipeline

from energia_app.exceptions import ConfigError
from energia_app.modeling.estimators import available_estimators, build_estimator, prefixed, register_estimator


@pytest.mark.parametrize("nombre", ["ridge", "hist_gradient_boosting", "random_forest"])
def test_cada_estimador_es_un_pipeline_con_paso_model(nombre):
    est = build_estimator(nombre, random_state=0)

    assert isinstance(est, Pipeline)
    assert est.steps[-1][0] == "model"


def test_ridge_escala_y_los_arboles_no():
    assert [n for n, _ in build_estimator("ridge").steps] == ["scale", "model"]
    assert [n for n, _ in build_estimator("hist_gradient_boosting").steps] == ["model"]


def test_el_espacio_del_yaml_se_traduce_al_pipeline():
    assert prefixed({"alpha": [1, 10]}) == {"model__alpha": [1, 10]}


def test_estimador_desconocido_dice_los_disponibles():
    with pytest.raises(ConfigError, match="Disponibles"):
        build_estimator("xgboost_magico")


def test_registrar_un_estimador_nuevo_sin_tocar_nada_mas():
    from sklearn.linear_model import Lasso

    @register_estimator("lasso_de_prueba")
    def _lasso(random_state):
        return Pipeline([("model", Lasso())])

    assert "lasso_de_prueba" in available_estimators()
    assert isinstance(build_estimator("lasso_de_prueba").steps[-1][1], Lasso)


def test_no_se_puede_registrar_dos_veces():
    with pytest.raises(ConfigError, match="Ya hay un estimador"):
        register_estimator("ridge")(lambda rs: None)
