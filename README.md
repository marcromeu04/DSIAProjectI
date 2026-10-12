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

- `sesiones/` — ejercicios de cada sesión y notas conceptuales
- `requirements.txt` — dependencias directas del proyecto

## Tests y cobertura

    pytest -q
    pytest -q -m "not integration"
    pytest -q --cov=ventas_app --cov-report=term-missing --cov-fail-under=60

## CI

`.github/workflows/ci.yml` se ejecuta en cada push a `main` y en cada pull request: instala Python 3.12 y las dependencias, lanza pytest y falla si la cobertura baja del 60 %.
