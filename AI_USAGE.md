# Uso de IA

## En el producto

El proyecto usa un modelo de lenguaje para una sola cosa: explicar una factura con palabras sencillas.
Las cifras (potencia recomendada, ahorro, penalización por reactiva y mejores horas) las calcula mi
código y el modelo de scikit-learn. El modelo de lenguaje solo las redacta.

- **Proveedor:** Hugging Face Inference Providers, con `huggingface_hub`.
- **Tarea:** `chat_completion`.
- **Modelo:** `mistralai/Mistral-7B-Instruct-v0.3` (se puede cambiar con `HF_MODEL`).
- **Por defecto funciona en modo `mock`:** devuelve un texto fijo, sin internet ni token. Así corren
  los tests y el CI. Para usar el modelo real hay que poner `AI_MODE=hf` y un `HF_TOKEN` en `.env`,
  que nunca se sube al repositorio.
- **Precauciones:** el prompt le prohíbe inventar cifras y le pide ignorar cualquier instrucción que
  venga dentro de los datos de la factura.

## En el desarrollo

He usado Claude (Anthropic) como apoyo, no como autor. Lo usé sobre todo para consultar cómo aplicar
un patrón, pedir propuestas que luego revisaba y que me explicara conceptos que no entendía. El trabajo
lo hice yo: aplicar cada cambio en mi repo, ejecutar y depurar los tests en mi máquina, resolver los
errores de entorno y de Git y decidir qué entraba en cada commit y en cada PR. Avancé commit a commit,
y cada PR pasa por el CI antes de mergearse.

Lo que no acepté tal cual:

- **El primer diseño del modelo.** Era un único algoritmo con parámetros fijos y las features metidas
  en el mismo fichero. Lo rechacé y exigí:
  - un `params.yaml` bien estructurado y validado;
  - búsqueda automática de hiperparámetros;
  - validación cruzada temporal;
  - varios candidatos comparados entre sí;
  - features desacopladas para poder ampliarlas sin tocar el entrenamiento.
- **Código que no entendía.** No incorporé ningún patrón sin que se explicara dónde y por qué se
  aplicaba (Template Method, Registry, Factory, Composite, Strategy, Facade) y qué principio SOLID cubría.
- **El reparto en commits.** La primera propuesta tenía pocos PR y commits demasiado grandes. Pedí
  dividirla en commits pequeños, cada uno con su comprobación. Además, descarté dos commits que ya había
  hecho y rehíce el trabajo desde `main` para que el historial quedara limpio.
- **Instrucciones que no funcionaban en mi entorno.** La instalación con `pip` fallaba en mi sistema
  (*externally-managed-environment*); pasé a gestionar el entorno con `uv`.
- **El periodo de test de 7 días.** Incluía un festivo que distorsionaba la evaluación; lo amplié a 30.
- **El cálculo del día siguiente.** Fallaba los días de cambio de hora; se corrigió y se añadió un test.
- **Un test que dependía del entrenamiento real.** Era lento y frágil; lo sustituí por una fixture con
  un modelo pequeño.
- **Un PR mergeado con el CI en rojo.** Me había saltado un paso; el CI lo detectó y lo arreglé en una
  rama aparte. Desde entonces no mergeo sin el CI en verde.

## Decisiones de fondo

Son decisiones mías, no de la herramienta:

- **El problema:** ayudar a las pymes a pagar menos luz, auditando la factura y prediciendo el precio
  de cada hora del día siguiente para saber cuándo consumir.
- **Los datos:** precios PVPC reales de Red Eléctrica y facturas sintéticas generadas con reglas del
  dominio, validados antes de usarse.
- **Desacoplamiento:** cada grupo de features es un bloque independiente que se registra por nombre.
  Añadir uno nuevo es crear una clase y una línea en `params.yaml`, sin tocar el entrenamiento.
- **Configuración fuera del código:** todo lo que cambia entre experimentos vive en `params.yaml` y
  se valida al cargar; un error se detecta antes de entrenar, no a mitad.
- **Evaluación honesta:** validación temporal sin fugas de información (ninguna feature mira menos de
  24 horas atrás), 30 días de test que no se tocan hasta el final y comparación obligatoria con dos
  atajos ingenuos.
- **Elegir el modelo por validación cruzada, no por el test:** el test se mira una sola vez, al final.
  Si se usara para elegir, la evaluación estaría inflada.
- **Los atajos ingenuos se tratan como modelos:** «igual que ayer» e «igual que hace una semana»
  tienen la misma interfaz que cualquier estimador de scikit-learn. Así se comparan en las mismas
  condiciones, y un modelo solo vale si les gana.
- **Trazabilidad:** junto al fichero del modelo se guardan las métricas, los resultados de cada
  combinación probada en la validación cruzada, qué modelo ganó y cuándo se entrenó. Con la semilla
  fijada en `params.yaml`, cualquier resultado se puede reproducir y explicar.
- **Features y modelo juntos:** el artefacto guarda ambos, para que nadie pueda predecir con features
  distintas de las del entrenamiento.
- **Patrones solo donde hacen falta:** el registro y la fábrica existen porque hay varias
  implementaciones reales (4 bloques de features y 3 modelos). Donde solo hay una, una función basta.
- **La IA, solo en el borde:** el modelo de lenguaje no calcula nada, funciona en `mock` por defecto y
  se puede sustituir sin tocar el resto.
- **Preparado para el Proyecto III:** la estructura permite añadir la API, el dashboard y el despliegue
  sin reescribir el núcleo.
