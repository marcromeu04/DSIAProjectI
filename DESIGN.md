# DESIGN — principios aplicados (E2 / Proyecto I)

| Principio | Fichero / símbolo | Por qué cumple |
| --- | --- | --- |
| SRP (responsabilidad única) | `ventas_app/loader.py`, `validator.py`, `metrics.py`, `cli.py` | Cada módulo tiene un solo motivo de cambio: formato de entrada, reglas de calidad, KPIs u orquestación. Cambiar una regla no toca el loader ni la CLI. |
| OCP (abierto/cerrado) | `validator._reasons` → lista `rules` | Añadir una regla es añadir una tupla `(máscara, motivo)` a la lista; el bucle que las aplica no se modifica. |
| DIP (inversión de dependencias) | `cli.run` depende de `load_sales` y `validate_sales` (contrato DataFrame) | El pipeline depende de "una función que devuelve un DataFrame con las columnas del contrato", no de "un CSV". Un `load_from_json` que devuelva el mismo contrato encaja sin tocar `metrics`. |

**Funciones puras e I/O en los bordes:** `validator` y `metrics` no leen disco ni imprimen; solo `loader` lee y solo `cli` escribe. Por eso se testean con un DataFrame de 4 filas en memoria.

**Errores explícitos:** `exceptions.py` define `DataLoadError` y `ValidationError`; la CLI los captura y devuelve código de salida 1.

**Clean code:** sin `print` de depuración (`logging`), sin números mágicos (`VALID_REGIONS` como constante con nombre), sin mutación de la entrada (`copy()`).

## Parte B — `energia_app`

| Principio | Fichero / símbolo | Por qué cumple |
| --- | --- | --- |
| SRP | `loader.py`, `validator.py`, `metrics.py`, `cli.py` | Mismo reparto que en la Parte A: formato de entrada, reglas de calidad, cálculos y orquestación. Cambiar el precio del kW solo toca `metrics.py`. |
| OCP | `validator._reasons` y `validator._price_reasons` → listas `rules` | Una regla nueva es una tupla más en la lista; el bucle que las aplica no cambia. Facturas y precios usan el mismo mecanismo. |
| DIP | `cli.run` depende de `load_invoices`, `load_prices`, `validate_invoices` y `validate_prices` (contrato DataFrame) | Si las facturas llegaran de una foto o de otra API en vez de un CSV, bastaría otro loader que devuelva las mismas columnas. |

**Independencia de la Parte A:** `energia_app` no importa nada de `ventas_app`; tiene sus propias excepciones
y su propio contrato de columnas. Comparten el patrón, no el código.

**Datos dinámicos:** `scripts/descargar_precios.py` descarga mes a mes (límite de la API) desde 2025 hasta
ayer y guarda junto al CSV un `.meta.json` con fuente, rango, filas y fecha de descarga. La lógica de partir
el rango (`tramos_mensuales`) es una función pura y se testea sin red.

**Fechas y zona horaria:** los precios llegan con `+01:00` o `+02:00` según la época del año. Se convierten a
UTC para validar (detectar duplicados reales) y a `Europe/Madrid` para medir por hora del día.

**Una regla corregida con datos reales:** la primera versión rechazaba precios ≤ 0 y marcó 34 horas
reales de septiembre de 2026 como inválidas (mediodías con excedente solar). Se cambió la regla a un rango
plausible (-500 a 1.000 EUR/MWh) y se añadió un test con un precio negativo real.

**Cálculo en código, no en un modelo:** las métricas de ahorro son funciones deterministas con constantes con
nombre (`MARGEN_POTENCIA`, `REACTIVA_LIMITE`, `EUR_KW_DIA`, `MAX_PRICE_EUR_MWH`). Cada cifra se puede
reproducir a mano, y los tests lo hacen.

**Limitaciones conocidas**

- Las facturas son sintéticas y los precios por kW y kWh son inventados: los euros son de demostración.
- Se usa una sola potencia contratada; una tarifa 3.0TD real tiene seis periodos.
- Los precios PVPC de REE tienen licencia de uso informativo y no comercial; un uso comercial necesita
  autorización de REE o una fuente con licencia abierta.
