from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sales_frame():
   
    return pd.DataFrame({
        "fecha": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "region": ["Norte", "Norte", "Sur", "Este"],
        "producto": ["Gateway", "Sensor A", "Gateway", "Hub IoT"],
        "unidades": [2, 10, 1, 0],
        "precio_unitario": [100.0, 5.0, 100.0, 80.0],
        "cliente_id": ["C001", "C001", "C002", "C003"],
    })


@pytest.fixture
def sales_csv(tmp_path, sales_frame):

    path = tmp_path / "ventas.csv"
    sales_frame.to_csv(path, index=False)
    return path


@pytest.fixture
def real_sales_csv():
    return ROOT / "data" / "ventas.csv"
