from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def invoices_frame():
    # F1 válida, F2 potencia < 15 kW, F3 consumo negativo, F4 válida con exceso de reactiva
    return pd.DataFrame({
        "id_factura": ["F1", "F2", "F3", "F4"],
        "sector": ["taller", "nave", "taller", "hosteleria"],
        "provincia": ["Madrid", "Madrid", "Sevilla", "Bilbao"],
        "tarifa": ["3.0TD", "3.0TD", "6.1TD", "3.0TD"],
        "fecha_inicio": ["2026-01-01"] * 4,
        "fecha_fin": ["2026-01-31"] * 4,
        "potencia_contratada_kw": [30, 10, 20, 20],
        "potencia_maxima_kw": [10.0, 8.0, 15.0, 18.0],
        "consumo_kwh": [1000, 500, -5, 1000],
        "reactiva_kvarh": [100, 50, 10, 500],
        "importe_total_eur": [300.0, 120.0, 80.0, 400.0],
    })


@pytest.fixture
def invoices_csv(tmp_path, invoices_frame):
    path = tmp_path / "facturas.csv"
    invoices_frame.to_csv(path, index=False)
    return path


@pytest.fixture
def prices_csv(tmp_path):
    path = tmp_path / "precios.csv"
    pd.DataFrame({
        "fecha_hora": ["2026-09-01T00:00", "2026-09-01T01:00"],
        "precio_eur_mwh": [100.0, 200.0],
    }).to_csv(path, index=False)
    return path


@pytest.fixture
def real_invoices_csv():
    return ROOT / "data" / "raw" / "facturas_luz.csv"


@pytest.fixture
def real_prices_csv():
    return ROOT / "data" / "raw" / "precios_pvpc.csv"
