"""CLI: python -m ventas_app.cli --input data/ventas.csv --output data/ventas_limpias.csv"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ventas_app import metrics
from ventas_app.exceptions import DataLoadError, ValidationError
from ventas_app.loader import load_sales
from ventas_app.validator import validate_sales

logger = logging.getLogger("ventas_app")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline de calidad de datos de ventas")
    parser.add_argument("--input", type=Path, required=True, help="CSV de ventas")
    parser.add_argument("--output", type=Path, default=None, help="CSV de filas válidas")
    parser.add_argument("--top", type=int, default=5)
    return parser.parse_args(argv)


def run(input_path: Path, output_path: Path | None = None, top: int = 5) -> dict:
    frame = load_sales(input_path)
    result = validate_sales(frame)
    logger.info("validas=%d invalidas=%d", result.n_valid, result.n_invalid)
    summary = {
        "n_valid": result.n_valid,
        "n_invalid": result.n_invalid,
        "total_revenue": metrics.total_revenue(result.valid),
        "by_region": metrics.revenue_by_region(result.valid),
        "by_product": metrics.revenue_by_product(result.valid),
        "top_clients": metrics.top_clients(result.valid, n=top),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.valid.to_csv(output_path, index=False)
        result.invalid.to_csv(output_path.with_name(output_path.stem + "_invalidas.csv"), index=False)
    return summary


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        s = run(args.input, args.output, args.top)
    except (DataLoadError, ValidationError) as exc:
        logger.error("%s", exc)
        return 1
    print(f"Validas: {s['n_valid']}  Invalidas: {s['n_invalid']}")
    print(f"Importe total: {s['total_revenue']:,.2f} EUR")
    print("\nPor region:\n", s["by_region"].to_string(index=False))
    print("\nPor producto:\n", s["by_product"].to_string(index=False))
    print(f"\nTop {args.top} clientes:\n", s["top_clients"].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
