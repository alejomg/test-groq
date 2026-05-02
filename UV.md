## Cambiar alias de python3 a python

Linux intenta evitar que se confunda la versión antigua (Python 2) con la moderna. Esto configura el sistema para que **python** apunte a la versión 3 de forma global.

*sudo apt update*
*sudo apt install python-is-python3*


## uv (El nuevo estándar de alto rendimiento)

Administrador de paquetes y de proyectos de Python

*curl -LsSf https://astral.sh/uv/install.sh | sh*

- Crear entorno virtual: *uv venv*

- Borrar entorno virtual: *rm -rf .venv*

### Usar uv en la forma tradicional con "pip"

- Activar entorno: *source .venv/bin/activate*
 
Con *uv* no hace falta activar el entorno virtual para instalar paquetes.

- Instalar un paquete: *uv pip install <paquete1> <paquete2>*

- Instalar los paquetes, y sus dependencias, listados en requirements.txt: *uv pip install -r requirements.txt*
 
### Usar uv en la forma moderna

- Inicializar el proyecto: *uv init* Esto creará un archivo *pyproject.toml* básico, *.python-version* y *README.md*.

- Añadir un paquete: *uv add <paquete1> <paquete2>*

- Añadir los paquetes, y sus dependencias, listados en requirements.txt para convertir requirements.txt al formato moderno: *uv add -r requirements.txt*


## Stack de desarrollo ligero

El objetivo principal es evitar que el editor "secuestre" toda la memoria, dejando espacio para que el intérprete de Python y el sistema respiren.

- Editor: Geany. Consumo mínimo (<100MB).
*sudo apt install geany*

- Navegador: Firefox. Intentar tener solo las pestañas de la documentación de FastAPI y localhost:8000/docs.

- Terminal: Xfce Terminal. Viene por defecto en Mint XFCE y es muy ligera para correr Uvicorn.

- Entorno Virtual: Obligatorio. Mantiene las lbrerías de FastAPI aisladas y ordenadas.
*python3 -m venv venv*


## Rendimiento de la memoria

**ZRAM** Si no está activo, instalar *zram-config*. Esto comprime los datos en la RAM antes de usar el disco (swap), lo que hace que la RAM rinda como si fuera un poco más.


## Ejecutar uvicorn desde la terminal

Desde la carpeta del proyecto. Limita los *workers* para asegurar que no se disparen múltiples procesos que intenten devorar la RAM simultáneamente.

### Usando uv en la forma tradicional con "pip"

*.venv/bin/python -m uvicorn app.main:app --reload --workers 1*

### Usando uv en la forma moderna

*uv run uvicorn app.main:app --reload --workers 1*
