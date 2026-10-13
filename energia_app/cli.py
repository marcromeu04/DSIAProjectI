"""CLI: python -m energia_app.cli --input data/raw/facturas_luz.csv --prices data/raw/precios_pvpc.csv"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from energia_app import metrics
from energia_app.exceptions import DataLoadError, ValidationError
from energia_app.loader import load_invoices, load_prices
from energia_app.validator import validate_invoices

logger = logging.getLogger("energia_app")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auditoría de facturas de luz de pymes")
    parser.add_argument("--input", type=Path, required=True, help="CSV de facturas")
    parser.add_argument("--prices", type=Path, default=None, help="CSV de precios PVPC")
    parser.add_argument("--output", type=Path, default=None, help="CSV de filas válidas")
    return parser.parse_args(argv)


def run(input_path: Path, prices_path: Path | None = None, output_path: Path | None = None) -> dict:
    frame = load_invoices(input_path)
    result = validate_invoices(frame)
    logger.info("validas=%d invalidas=%d", result.n_valid, result.n_invalid)
    summary = {
        "n_valid": result.n_valid,
        "n_invalid": result.n_invalid,
        "total_savings": metrics.total_savings(result.valid),
        "total_reactive": metrics.total_reactive_penalty(result.valid),
        "oversized_share": metrics.oversized_share(result.valid),
        "by_sector": metrics.savings_by_sector(result.valid),
        "pvpc_avg": None,
    }
    if prices_path is not None:
        summary["pvpc_avg"] = metrics.average_pvpc_price(load_prices(prices_path))
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.valid.to_csv(output_path, index=False)
        result.invalid.to_csv(output_path.with_name(output_path.stem + "_invalidas.csv"), index=False)
    return summary


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    try:
        s = run(args.input, args.prices, args.output)
    except (DataLoadError, ValidationError) as exc:
        logger.error("%s", exc)
        return 1
    print(f"Validas: {s['n_valid']}  Invalidas: {s['n_invalid']}")
    print(f"Ahorro potencial por potencia: {s['total_savings']:,.2f} EUR")
    print(f"Penalizacion por reactiva: {s['total_reactive']:,.2f} EUR")
    print(f"Facturas con potencia sobredimensionada: {s['oversized_share']:.0%}")
    if s["pvpc_avg"] is not None:
        print(f"Precio medio PVPC: {s['pvpc_avg']:.2f} EUR/MWh")
    print("\nPor sector:\n", s["by_sector"].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
