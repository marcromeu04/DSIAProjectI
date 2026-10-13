"""Descarga el precio horario PVPC de REData (Red Eléctrica) a un CSV."""
import argparse
import json
from urllib.request import urlopen

import pandas as pd

URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"


def descargar(inicio: str, fin: str) -> pd.DataFrame:
    
    url = f"{URL}?start_date={inicio}T00:00&end_date={fin}T23:59&time_trunc=hour"
    with urlopen(url, timeout=30) as respuesta:
        datos = json.load(respuesta)

    
    for serie in datos["included"]:
        if "PVPC" in serie["attributes"]["title"]:
            df = pd.DataFrame(serie["attributes"]["values"])
            df = df[["datetime", "value"]]
            df.columns = ["fecha_hora", "precio_eur_mwh"]
            return df
    raise ValueError("No he encontrado la serie PVPC en la respuesta")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", default="2026-09-01")
    parser.add_argument("--fin", default="2026-09-30")
    parser.add_argument("--salida", default="data/raw/precios_pvpc.csv")
    args = parser.parse_args()

    df = descargar(args.inicio, args.fin)
    df.to_csv(args.salida, index=False)
    print(f"{len(df)} filas guardadas en {args.salida}")


if __name__ == "__main__":
    main()
