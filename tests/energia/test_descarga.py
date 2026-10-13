from datetime import date

import pandas as pd

from scripts import descargar_precios
from scripts.descargar_precios import tramos_mensuales


def test_tramos_parten_por_meses():
    tramos = tramos_mensuales(date(2025, 1, 15), date(2025, 3, 10))

    assert tramos == [
        (date(2025, 1, 15), date(2025, 1, 31)),
        (date(2025, 2, 1), date(2025, 2, 28)),
        (date(2025, 3, 1), date(2025, 3, 10)),
    ]


def test_tramos_cruzan_el_cambio_de_anio():
    tramos = tramos_mensuales(date(2025, 12, 20), date(2026, 1, 5))

    assert tramos[-1] == (date(2026, 1, 1), date(2026, 1, 5))


def test_descargar_junta_tramos_sin_red(monkeypatch):
    # Sustituimos la llamada a la API por una falsa: el test no usa internet
    def falso(desde, hasta):
        return pd.DataFrame({
            "fecha_hora": [f"{desde}T00:00", f"{hasta}T23:00"],
            "precio_eur_mwh": [100.0, 120.0],
        })

    monkeypatch.setattr(descargar_precios, "descargar_tramo", falso)

    df = descargar_precios.descargar(date(2025, 1, 1), date(2025, 2, 28), pausa=0)

    assert len(df) == 4
    assert list(df.columns) == ["fecha_hora", "precio_eur_mwh"]
