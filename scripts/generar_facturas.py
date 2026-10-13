"""Genera facturas de luz sintéticas de pymes de más de 15 kW."""
import argparse
import random
from datetime import date, timedelta

import pandas as pd

SECTORES = ["carpinteria", "taller", "nave", "hosteleria", "instalador"]
PROVINCIAS = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Bilbao"]
TARIFAS = ["3.0TD", "6.1TD"]

# Precios aproximados para calcular el importe (son inventados, no reales)
EUR_KW_DIA = 0.07
EUR_KWH = 0.14
EUR_KVARH = 0.04


def _factura(i: int, rng: random.Random) -> dict:
    # Una factura válida: potencias y consumos coherentes entre sí
    inicio = date(2026, 1, 1) + timedelta(days=rng.randint(0, 240))
    dias = rng.choice([28, 30, 31])
    contratada = rng.randint(16, 60)
    maximetro = round(contratada * rng.uniform(0.3, 1.1), 1)
    consumo = round(maximetro * dias * rng.uniform(2, 6))
    reactiva = round(consumo * rng.uniform(0, 0.45))

    # La reactiva solo se penaliza si pasa del 33 % de la energía activa
    exceso = max(0, reactiva - 0.33 * consumo)
    importe = (
        contratada * dias * EUR_KW_DIA + consumo * EUR_KWH + exceso * EUR_KVARH
    )
    return {
        "id_factura": f"F{i:04d}",
        "sector": rng.choice(SECTORES),
        "provincia": rng.choice(PROVINCIAS),
        "tarifa": rng.choice(TARIFAS),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(days=dias)).isoformat(),
        "potencia_contratada_kw": contratada,
        "potencia_maxima_kw": maximetro,
        "consumo_kwh": consumo,
        "reactiva_kvarh": reactiva,
        "importe_total_eur": round(importe, 2),
    }


def _estropear(fila: dict, tipo: int) -> dict:
    # Cada tipo rompe una regla distinta del validador
    if tipo == 0:
        fila["potencia_contratada_kw"] = 10  # por debajo de 15 kW
    elif tipo == 1:
        fila["fecha_fin"] = fila["fecha_inicio"]  # periodo de 0 días
    elif tipo == 2:
        fila["consumo_kwh"] = -abs(fila["consumo_kwh"]) - 1  # consumo negativo
    elif tipo == 3:
        fila["tarifa"] = "2.0TD"  # tarifa de hogar, no de pyme
    else:
        fila["importe_total_eur"] = ""  # importe vacío
    return fila


def generar(n: int = 200, invalidas: int = 20, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    filas = [_factura(i + 1, rng) for i in range(n)]
    # Estropeamos un número exacto de filas, repartidas entre los 5 tipos
    for k, idx in enumerate(rng.sample(range(n), invalidas)):
        filas[idx] = _estropear(filas[idx], k % 5)
    return pd.DataFrame(filas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--invalidas", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--salida", default="data/raw/facturas_luz.csv")
    args = parser.parse_args()

    df = generar(args.n, args.invalidas, args.seed)
    df.to_csv(args.salida, index=False)
    print(f"{len(df)} facturas guardadas en {args.salida}")


if __name__ == "__main__":
    main()

