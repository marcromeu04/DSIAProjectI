# DESIGN — principios aplicados (E2 / Proyecto I)

| Principio | Fichero / símbolo | Por qué cumple |
| --- | --- | --- |
| SRP (responsabilidad única) | `ventas_app/loader.py`, `validator.py`, `metrics.py`, `cli.py` | Cada módulo tiene un solo motivo de cambio: formato de entrada, reglas de calidad, KPIs u orquestación. Cambiar una regla no toca el loader ni la CLI. |
| OCP (abierto/cerrado) | `validator._reasons` → lista `rules` | Añadir una regla es añadir una tupla `(máscara, motivo)` a la lista; el bucle que las aplica no se modifica. |
| DIP (inversión de dependencias) | `cli.run` depende de `load_sales` y `validate_sales` (contrato DataFrame) | El pipeline depende de "una función que devuelve un DataFrame con las columnas del contrato", no de "un CSV". Un `load_from_json` que devuelva el mismo contrato encaja sin tocar `metrics`. |

**Funciones puras e I/O en los bordes:** `validator` y `metrics` no leen disco ni imprimen; solo `loader` lee y solo `cli` escribe. Por eso se testean con un DataFrame de 4 filas en memoria.

**Errores explícitos:** `exceptions.py` define `DataLoadError` y `ValidationError`; la CLI los captura y devuelve código de salida 1.

**Clean code:** sin `print` de depuración (`logging`), sin números mágicos (`VALID_REGIONS` como constante con nombre), sin mutación de la entrada (`copy()`).
