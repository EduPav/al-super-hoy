"""El gate canonico: lo que hay que correr antes de dar un cambio por bueno.

`python -m herramientas.verificar`

Corre, en orden y cortando en el primer fallo:

1. el chequeo de la superficie de instrucciones (sin dependencias);
2. ruff sobre el codigo Python;
3. las pruebas.

Primero las instrucciones porque es el gate que no necesita nada instalado: si
la documentacion ya esta rota, arreglarla antes evita revisar dos veces.

Sin red y sin credenciales: las pruebas tienen prohibido abrir sockets
(`pruebas/conftest.py`), asi que este comando da lo mismo en tu maquina, en CI
y a las tres de la madrugada con MODO caido.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (etiqueta, comando, pista cuando falta la herramienta)
PASOS = (
    ("instrucciones", [sys.executable, "-m", "herramientas.instrucciones"], None),
    ("ruff", [sys.executable, "-m", "ruff", "check", "."], "ruff"),
    ("pruebas", [sys.executable, "-m", "pytest"], "pytest"),
)


def _disponible(modulo: str | None) -> bool:
    if modulo is None:
        return True
    import importlib.util

    return importlib.util.find_spec(modulo) is not None


def main() -> int:
    if shutil.which(sys.executable) is None:  # pragma: no cover - defensivo
        print("No se pudo ubicar el interprete de Python.")
        return 1

    for etiqueta, comando, modulo in PASOS:
        if not _disponible(modulo):
            print(f"\n== {etiqueta}: FALTA {modulo}")
            print(f"   pip install -r requirements-dev.txt  # instala {modulo}")
            return 1

        print(f"\n== {etiqueta}")
        codigo = subprocess.run(comando, cwd=RAIZ, check=False).returncode
        if codigo != 0:
            print(
                f"\nFallo el paso '{etiqueta}'. Que revisa cada gate y como salir del "
                "fallo: documentacion/verificacion.md"
            )
            return codigo

    print("\nTodo verde. Falta lo que ninguna prueba puede ver: correr "
          "`python -m ingesta.main` si tocaste una fuente, y mirar el mapeo de comercios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
