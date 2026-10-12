# Sesión 01 — Entornos virtuales y Git/GitHub

## 1. ¿Qué es un venv y qué problema resuelve?
Es una carpeta (.venv) con un Python privado del proyecto. Permite que dos proyectos
usen versiones distintas de pandas sin pisarse. Lo creo con uv venv y lo activo con
source .venv/bin/activate.

## 2. ¿Por qué .venv no se sube a Git?
Porque se regenera: con requirements.txt y uv pip install lo reconstruyo en cualquier
ordenador, así que subirlo solo añadiría peso y ficheros que solo sirven en mi máquina.
No se sube porque una regla de .gitignore lo cubre, no porque empiece por punto.

## 3. ¿Qué es un commit y qué es el staging?
Un commit es una foto del proyecto en ese momento, con un mensaje que dice qué cambió.
El staging es la lista de ficheros que he seleccionado con git add para que entren en la
próxima foto. Lo que no añado no entra aunque lo haya modificado.

## 4. ¿Cómo es el flujo de trabajo rama → PR → merge?
Creo una rama como banco de pruebas, hago commits ahí sin tocar main, la subo con git push
y abro una Pull Request para que se revise. Si funciona, el merge mueve main hasta mi
último commit.

## 5. ¿Para qué sirve .gitignore?
Es la lista de lo que Git no debe guardar nunca: el entorno virtual, las cachés de Python
y los secretos como .env. Lo que no está en Git no acaba en GitHub por error.
