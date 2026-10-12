from ventas_app import metrics
from ventas_app.validator import validate_sales


def test_total_revenue(sales_frame):
    valid = validate_sales(sales_frame).valid
    assert metrics.total_revenue(valid) == 350.0  # 2*100 + 10*5 + 1*100


def test_revenue_by_region_ordenado(sales_frame):
    valid = validate_sales(sales_frame).valid
    out = metrics.revenue_by_region(valid)
    assert list(out["region"]) == ["Norte", "Sur"]  # Norte 250 > Sur 100
    assert out["importe"].iloc[0] == 250.0


def test_top_clients_limita_n(sales_frame):
    valid = validate_sales(sales_frame).valid
    assert len(metrics.top_clients(valid, n=1)) == 1

