from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  
CSV = ROOT / "data" / "ventas.csv"          

tabla = pd.read_csv(CSV)                    

print("shape:", tabla.shape)                
print("\ndtypes:\n", tabla.dtypes)          
print("\nnulos:\n", tabla.isna().sum())     


unidades = pd.to_numeric(tabla["unidades"], errors="coerce")      
precio = pd.to_numeric(tabla["precio_unitario"], errors="coerce")


sospechosas = tabla[unidades.isna() | (unidades <= 0) | precio.isna() | (precio <= 0)]
print("\nfilas sospechosas:\n", sospechosas)

print("\nregiones:", tabla["region"].unique())                       
print("fechas invalidas:", pd.to_datetime(tabla["fecha"], errors="coerce").isna().sum())   
