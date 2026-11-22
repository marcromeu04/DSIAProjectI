"""CLI: python -m energia_app.cli --input data/raw/facturas_luz.csv --prices data/raw/precios_pvpc.csv"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from energia_app import metrics
from energia_app.ai_client import AIClient, AIClientError, ExplainRequest
from energia_app.exceptions import ConfigError, DataLoadError, FeatureError, ValidationError
from energia_app.features.builder import price_series
from energia_app.loader import load_invoices, load_prices
from energia_app.modeling.bundle import ModelBundle
from energia_app.validator import validate_invoices, validate_prices

logger = logging.getLogger("energia_app")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Lee los argumentos; argv permite pasarlos a mano desde los tests."""
    parser = argparse.ArgumentParser(description="Auditoría de facturas de luz de pymes")
    parser.add_argument("--input", type=Path, required=True, help="CSV de facturas")
    parser.add_argument("--prices", type=Path, default=None, help="CSV de precios PVPC")
    parser.add_argument("--output", type=Path, default=None, help="CSV de filas válidas")
    parser.add_argument("--model", type=Path, default=None,
                        help="Modelo entrenado (.joblib); con --prices predice el precio de cada hora de mañana")
    parser.add_argument("--explain", default=None, metavar="ID_FACTURA",
                        help="Explica una factura en lenguaje llano (AI_MODE=mock|hf)")
    return parser.parse_args(argv)


def explain_request(valid, id_factura: str, mejores_horas: list[str]) -> ExplainRequest:
    """Construye la petición al LLM con las cifras de una factura ya validada."""
    frame = metrics.with_savings(valid)
    filas = frame[frame["id_factura"] == id_factura]
    if filas.empty:
        raise ValueError(f"No hay ninguna factura válida con id {id_factura}")
    fila = filas.iloc[0]
    return ExplainRequest(
        id_factura=id_factura,
        sector=str(fila["sector"]),
        potencia_contratada_kw=float(fila["potencia_contratada_kw"]),
        potencia_optima_kw=float(fila["potencia_optima_kw"]),
        ahorro_potencia_eur=round(float(fila["ahorro_potencia_eur"]), 2),
        penalizacion_reactiva_eur=round(float(fila["penalizacion_reactiva_eur"]), 2),
        mejores_horas=mejores_horas,
    )


def run(input_path: Path, prices_path: Path | None = None, output_path: Path | None = None,
        model_path: Path | None = None, explain_id: str | None = None,
        ai_client: AIClient | None = None) -> dict:
    """Ejecuta el pipeline completo y devuelve un resumen (sin imprimir nada).

    Separarlo de main() permite testear el resultado sin pasar por la terminal.
    """
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
    # Los precios son opcionales: sin --prices la auditoría funciona igual
    if prices_path is not None:
        prices = validate_prices(load_prices(prices_path))
        logger.info("horas validas=%d invalidas=%d", prices.n_valid, prices.n_invalid)
        summary["prices_valid"] = prices.n_valid
        summary["prices_invalid"] = prices.n_invalid
        summary["pvpc_avg"] = metrics.average_pvpc_price(prices.valid)
        summary["pvpc_spread"] = metrics.peak_valley_spread(prices.valid)
        summary["pvpc_by_hour"] = metrics.price_by_hour(prices.valid)
        # Inferencia integrada en el pipeline: el modelo guardado predice cada hora de mañana
        if model_path is not None:
            bundle = ModelBundle.load(model_path)
            summary["forecast"] = bundle.predict_next_day(price_series(prices.valid, bundle.target))
            logger.info("prevision de %d horas con el modelo %s", len(summary["forecast"]),
                        bundle.metadata.get("ganador", "?"))
    # Explicación en lenguaje llano: las cifras salen de metrics y del modelo, el LLM solo redacta
    if explain_id is not None:
        horas: list[str] = []
        if summary.get("forecast") is not None:
            baratas = summary["forecast"].nsmallest(3, "precio_previsto_eur_mwh")
            horas = [f"{t:%H:%M}" for t in baratas["fecha_hora"]]
        req = explain_request(result.valid, explain_id, horas)
        summary["explanation"] = (ai_client or AIClient.from_env()).explain(req)

    # Las inválidas se guardan aparte con su motivo para poder revisarlas
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.valid.to_csv(output_path, index=False)
        result.invalid.to_csv(output_path.with_name(output_path.stem + "_invalidas.csv"), index=False)
    return summary


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada. Devuelve 0 si todo va bien y 1 si hay un error de datos."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv()  # lee AI_MODE, HF_TOKEN y HF_MODEL del .env si existe
    args = parse_args(argv)
    try:
        s = run(args.input, args.prices, args.output, args.model, args.explain)
    except (DataLoadError, ValidationError, ConfigError, FeatureError, FileNotFoundError, ValueError,
            AIClientError) as exc:
        # Error esperado (fichero mal): mensaje claro y código 1, sin traza larga
        logger.error("%s", exc)
        return 1
    print(f"Validas: {s['n_valid']}  Invalidas: {s['n_invalid']}")
    print(f"Ahorro potencial por potencia: {s['total_savings']:,.2f} EUR")
    print(f"Penalizacion por reactiva: {s['total_reactive']:,.2f} EUR")
    print(f"Facturas con potencia sobredimensionada: {s['oversized_share']:.0%}")
    if s["pvpc_avg"] is not None:
        print(f"\nPrecios PVPC: {s['prices_valid']} horas validas, {s['prices_invalid']} invalidas")
        print(f"Precio medio PVPC: {s['pvpc_avg']:.2f} EUR/MWh")
        print(f"Diferencia hora cara - hora barata: {s['pvpc_spread']:.2f} EUR/MWh")
        caras = s["pvpc_by_hour"].nlargest(3, "precio_eur_mwh")
        print("Horas mas caras:\n", caras.to_string(index=False))
    if s.get("forecast") is not None:
        prevision = s["forecast"]
        print(f"\nPrevision para {prevision['fecha_hora'].iloc[0].date()}: "
              f"media {prevision['precio_previsto_eur_mwh'].mean():.2f} EUR/MWh")
        print("Mejores horas para consumir:")
        for _, fila in prevision.nsmallest(3, "precio_previsto_eur_mwh").iterrows():
            print(f"  {fila['fecha_hora']:%H:%M}  {fila['precio_previsto_eur_mwh']:.2f} EUR/MWh")
    print("\nPor sector:\n", s["by_sector"].to_string(index=False))
    if s.get("explanation") is not None:
        exp = s["explanation"]
        print(f"\nExplicacion ({exp.provider}, {exp.model}):\n{exp.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
