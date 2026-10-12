import pandas as pd
import pytest

from ventas_app.exceptions import ValidationError
from ventas_app.validator import validate_sales


def test_separa_validas_e_invalidas(sales_frame):
    result = validate_sales(sales_frame)
    assert result.n_valid == 3
    assert result.n_invalid == 1
    assert result.invalid["motivo"].iloc[0] == "unidades <= 0"


def test_no_modifica_la_entrada(sales_frame):
    antes = sales_frame.copy()
    validate_sales(sales_frame)
    pd.testing.assert_frame_equal(sales_frame, antes)


@pytest.mark.parametrize("unidades, precio, esperado", [
    (0, 10.0, "unidades <= 0"),
    (-1, 10.0, "unidades <= 0"),
    ("na", 10.0, "unidades no numericas o nulas"),
    (None, 10.0, "unidades no numericas o nulas"),
    (3, 0.0, "precio <= 0"),
    (3, -5.0, "precio <= 0"),
    (3, None, "precio nulo"),
    (1, 1.0, None),  # el unico caso valido
])
def test_casos_borde(unidades, precio, esperado):
    frame = pd.DataFrame({
        "fecha": ["2026-01-01"], "region": ["Norte"], "producto": ["X"],
        "unidades": [unidades], "precio_unitario": [precio], "cliente_id": ["C1"],
    })
    result = validate_sales(frame)
    if esperado is None:
        assert result.n_valid == 1
    else:
        assert result.n_valid == 0
        assert esperado in result.invalid["motivo"].iloc[0]


def test_faltan_columnas():
    with pytest.raises(ValidationError):
        validate_sales(pd.DataFrame({"fecha": ["2026-01-01"]}))
