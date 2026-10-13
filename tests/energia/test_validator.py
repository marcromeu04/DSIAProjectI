import pytest

from energia_app.exceptions import ValidationError
from energia_app.loader import load_invoices
from energia_app.validator import validate_invoices


def test_separa_validas_e_invalidas(invoices_frame):
    result = validate_invoices(invoices_frame)

    assert result.n_valid == 2
    assert result.n_invalid == 2
    assert list(result.valid["id_factura"]) == ["F1", "F4"]


@pytest.mark.parametrize(
    "columna, valor, motivo",
    [
        ("potencia_contratada_kw", 10, "potencia contratada"),
        ("consumo_kwh", -1, "consumo negativo"),
        ("tarifa", "2.0TD", "tarifa desconocida"),
        ("fecha_fin", "2026-01-01", "periodo sin dias"),
        ("fecha_inicio", "no-es-fecha", "fecha invalida"),
        ("importe_total_eur", None, "importe nulo"),
    ],
)
def test_cada_regla_rechaza_su_caso(invoices_frame, columna, valor, motivo):
    frame = invoices_frame.iloc[[0]].copy()
    frame[columna] = valor

    result = validate_invoices(frame)

    assert result.n_valid == 0
    assert motivo in result.invalid["motivo"].iloc[0]


def test_faltan_columnas(invoices_frame):
    with pytest.raises(ValidationError, match="Faltan columnas"):
        validate_invoices(invoices_frame.drop(columns=["tarifa"]))


@pytest.mark.integration
def test_facturas_reales_180_y_20(real_invoices_csv):
    result = validate_invoices(load_invoices(real_invoices_csv))

    assert (result.n_valid, result.n_invalid) == (180, 20)

