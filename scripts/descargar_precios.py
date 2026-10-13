"""Descarga el precio horario PVPC de REData (Red Eléctrica) a un CSV."""
import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
INICIO_POR_DEFECTO = "2025-01-01"


def tramos_mensuales(inicio: date, fin: date) -> list[tuple[date, date]]:
    # La API solo deja pedir un mes de datos horarios en cada llamada
    tramos = []
    actual = inicio
    while actual <= fin:
        siguiente_mes = (actual.replace(day=1) + timedelta(days=32)).replace(day=1)
        tramos.append((actual, min(siguiente_mes - timedelta(days=1), fin)))
        actual = siguiente_mes
    return tramos


def descargar_tramo(inicio: date, fin: date) -> pd.DataFrame:
    url = f"{URL}?start_date={inicio}T00:00&end_date={fin}T23:59&time_trunc=hour"
    with urlopen(url, timeout=30) as respuesta:
        datos = json.load(respuesta)

    # La respuesta trae varias series; nos quedamos con la del PVPC
    for serie in datos["included"]:
        if "PVPC" in serie["attributes"]["title"]:
            df = pd.DataFrame(serie["attributes"]["values"])[["datetime", "value"]]
            df.columns = ["fecha_hora", "precio_eur_mwh"]
            return df
    raise ValueError(f"No hay serie PVPC entre {inicio} y {fin}")


def descargar(inicio: date, fin: date, pausa: float = 0.5) -> pd.DataFrame:
    partes = []
    for desde, hasta in tramos_mensuales(inicio, fin):
        print(f"Descargando {desde} -> {hasta}")
        partes.append(descargar_tramo(desde, hasta))
        time.sleep(pausa)  # para no saturar la API
    df = pd.concat(partes, ignore_index=True)
    return df.drop_duplicates(subset="fecha_hora").reset_index(drop=True)


def main() -> None:
    ayer = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", default=INICIO_POR_DEFECTO)
    parser.add_argument("--fin", default=ayer.isoformat())
    parser.add_argument("--salida", default="data/raw/precios_pvpc.csv")
    args = parser.parse_args()

    inicio = date.fromisoformat(args.inicio)
    fin = date.fromisoformat(args.fin)
    df = descargar(inicio, fin)
    df.to_csv(args.salida, index=False)

    # Guardamos de dónde y cuándo salen los datos (lo pide el enunciado)
    meta = {
        "fuente": URL,
        "serie": "PVPC",
        "inicio": args.inicio,
        "fin": args.fin,
        "filas": len(df),
        "descargado": datetime.now().isoformat(timespec="seconds"),
    }
    Path(args.salida).with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(df)} filas guardadas en {args.salida}")


if __name__ == "__main__":
    main()
