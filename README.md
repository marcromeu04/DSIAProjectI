# DSIA 2026-27 — Marc Romeu
![CI](https://github.com/marcromeu04/DSIAProjectI/actions/workflows/ci.yml/badge.svg)

Repositorio de prácticas y proyectos de la asignatura Desarrollo de Sistemas Inteligentes Aplicados.
Python 3.12, entorno gestionado con uv.

## Instalación

    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -r requirements.txt
    python sesiones/sesion01/check_entorno.py --strict   # debe decir ENTORNO OK

## Estructura

- `ventas_app/` — Proyecto I, Parte A: pipeline de ventas (`data/ventas.csv`)
- `energia_app/` — Proyecto I, Parte B: auditoría de facturas de luz de pymes y precios PVPC
- `scripts/` — descarga de precios públicos y generador de facturas sintéticas
- `tests/` — tests de las dos partes (`tests/ventas/`, `tests/energia/`)
- `sesiones/` — ejercicios de cada sesión y notas conceptuales
- `requirements.txt` — dependencias directas del proyecto

## Proyecto I — Parte A: ventas

Pipeline `loader → validator → metrics → cli` sobre el CSV de ventas del curso.

    python -m ventas_app.cli --input data/ventas.csv --output data/ventas_limpias.csv

Salida esperada: 140 filas válidas y 10 inválidas (guardadas con su motivo en
`data/ventas_limpias_invalidas.csv`), importe total, ventas por región, por producto y top de clientes.

## Proyecto I — Parte B: auditoría de facturas de luz de pymes

Pipeline `loader → validator → metrics → cli` en `energia_app/`, independiente de la Parte A.
Trabaja con dos datasets:

- **Precios PVPC reales** (dinámico, más de 10.000 filas): precio horario de la electricidad desde el
  1 de enero de 2025 hasta ayer. Cada vez que se ejecuta la descarga se añaden los días nuevos.
- **Facturas de pymes de más de 15 kW** (sintético, 10.000 filas): sobre ellas se calcula cuánto se
  podría ahorrar ajustando la potencia contratada y evitando penalizaciones por energía reactiva.

### Datos

| Fichero | Origen | Notas |
|---|---|---|
| `data/raw/precios_pvpc.csv` | Red Eléctrica, REData API: [mercados / precios en tiempo real](https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real), serie PVPC, EUR/MWh por hora | Unas 15.600 filas (2025-01-01 → ayer). Rango, número de filas y fecha de descarga en `data/raw/precios_pvpc.meta.json`. Fuente: Red Eléctrica |
| `data/raw/facturas_luz.csv` | Sintético, `scripts/generar_facturas.py` (semilla 42) | 10.000 facturas: 9.000 válidas y 1.000 con un error deliberado (200 de cada tipo) |

La API de REData solo devuelve un mes de datos horarios por petición, así que el script descarga
mes a mes y junta el resultado.

**Licencia de los precios.** REE no publica una licencia abierta: su [aviso legal](https://www.ree.es/es/aviso-legal)
permite reutilizar el contenido con fines informativos y no comerciales (por ejemplo, académicos), citando a
Red Eléctrica como fuente y la fecha de actualización y sin alterar los datos. Aquí se usa solo con fin
académico; un uso comercial requeriría su autorización previa.

Los importes y los precios por kW y por kWh de las facturas son inventados: los resultados en euros son de
demostración y no representan el mercado real.

### Cómo ejecutarlo

    python scripts/descargar_precios.py      # descarga (o actualiza) los precios hasta ayer
    python scripts/generar_facturas.py       # genera las 10.000 facturas sintéticas
    python -m energia_app.cli --input data/raw/facturas_luz.csv \
        --prices data/raw/precios_pvpc.csv --output data/processed/facturas_validas.csv

Salida esperada: 9.000 facturas válidas y 1.000 inválidas (guardadas con su motivo en
`data/processed/facturas_validas_invalidas.csv`), ahorro y penalización totales y por sector,
número de horas de precio válidas, precio medio, diferencia pico-valle y las tres horas más caras.
`data/processed/` no se versiona: se regenera con el comando anterior.

### Reglas de validación

- **Facturas:** potencia contratada ≥ 15 kW; maxímetro, consumo y reactiva no negativos; importe positivo;
  fechas válidas y periodo de al menos un día; tarifa 3.0TD o 6.1TD.
- **Precios:** fecha válida; sin horas duplicadas (comparadas en UTC para no confundir el cambio de hora);
  precio presente y entre -500 y 1.000 EUR/MWh. Los precios negativos se aceptan porque son reales:
  en la descarga hay horas de mediodía con precio negativo (por ejemplo, el 5 y 6 de septiembre de 2026),
  cuando sobra producción solar.

### Métricas

Facturas:

1. Ahorro por potencia: kW contratados por encima del maxímetro + 5 % (mínimo 15 kW) × días × precio del kW.
2. Penalización por reactiva: exceso sobre el 33 % del consumo × precio del kvarh.
3. Ahorro y penalización por sector.
4. Porcentaje de facturas con potencia sobredimensionada.

Precios:

5. Precio medio PVPC del periodo.
6. Precio medio por hora del día (hora de Madrid) y por mes.
7. Diferencia pico-valle: lo que se ahorra, de media, moviendo 1 MWh de la hora más cara a la más barata.

## Tests y cobertura

    pytest -q
    pytest -q -m "not integration"
    pytest -q --cov=ventas_app --cov=energia_app --cov-report=term-missing --cov-fail-under=60

Los tests marcados `integration` usan los CSV reales del repositorio. El resto trabaja con datos en
memoria o en `tmp_path`, sin red: la descarga de precios se prueba sustituyendo la llamada a la API
con `monkeypatch`.

## CI

`.github/workflows/ci.yml` se ejecuta en cada push a `main` y en cada pull request: instala Python 3.12 y
las dependencias, lanza pytest sobre las dos partes y falla si la cobertura de `ventas_app` + `energia_app`
baja del 60 %.
