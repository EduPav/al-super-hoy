"""Chequeo del entorno antes de correr nada.

`python -m herramientas.doctor`

Contesta la pregunta "¿por que me falla?" antes de que falle, con el comando
exacto para arreglarlo. Sin esto, la ingesta muere con un ImportError y el
agente que la corre tiene que deducir que faltaba instalar dependencias.

Solo biblioteca estandar: es lo primero que se corre, justamente cuando todavia
no hay nada instalado.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

PYTHON_MINIMO = (3, 10)

# Lo que necesita la ingesta para correr, con el paquete que lo trae.
DEPENDENCIAS = (
    ("requests", "requests", "requirements.txt"),
    ("yaml", "PyYAML", "requirements.txt"),
    ("bs4", "beautifulsoup4", "requirements.txt"),
)

# Lo que necesita `python -m herramientas.verificar`. Su ausencia no impide
# correr la ingesta, asi que es aviso y no error.
DESARROLLO = (("pytest", "pytest"), ("ruff", "ruff"))

# Archivos sin los cuales la ingesta no puede decidir nada.
DATOS = (
    ("datos/comercios-santa-fe.yml", "el registro de comercios: sin el no hay filtro de zona"),
)

fallos: list[tuple[str, str]] = []
avisos: list[tuple[str, str]] = []


def _falla(que: str, arreglo: str) -> None:
    fallos.append((que, arreglo))


def _avisa(que: str, arreglo: str) -> None:
    avisos.append((que, arreglo))


def _python() -> None:
    actual = sys.version_info[:2]
    if actual < PYTHON_MINIMO:
        _falla(
            f"Python {actual[0]}.{actual[1]} es viejo para este repo",
            f"instala Python {PYTHON_MINIMO[0]}.{PYTHON_MINIMO[1]} o mas nuevo "
            "(el codigo usa `int | None` en anotaciones)",
        )


def _dependencias() -> None:
    faltan = [
        paquete
        for modulo, paquete, _ in DEPENDENCIAS
        if importlib.util.find_spec(modulo) is None
    ]
    if faltan:
        _falla(
            f"faltan dependencias de la ingesta: {', '.join(faltan)}",
            "pip install -r requirements.txt",
        )

    faltan_dev = [
        paquete for modulo, paquete in DESARROLLO if importlib.util.find_spec(modulo) is None
    ]
    if faltan_dev:
        _avisa(
            f"faltan herramientas de desarrollo: {', '.join(faltan_dev)}",
            "pip install -r requirements-dev.txt "
            "(sin ellas `python -m herramientas.verificar` no corre entero)",
        )


def _datos() -> None:
    for relativo, para_que in DATOS:
        if not (RAIZ / relativo).exists():
            _falla(f"falta {relativo}: {para_que}", f"restaura {relativo} desde git")

    salida = RAIZ / "docs" / "datos" / "promos.json"
    if not salida.exists():
        _avisa(
            "todavia no hay docs/datos/promos.json",
            "python -m ingesta.main (la web no muestra nada hasta que exista)",
        )


def _git() -> None:
    if shutil.which("git") is None:
        _avisa(
            "git no esta en el PATH",
            "instala git; sin el, el chequeo de archivos ignorados queda omitido",
        )


def main() -> int:
    _python()
    _dependencias()
    _datos()
    _git()

    for que, arreglo in avisos:
        print(f"AVISO   {que}\n        -> {arreglo}")
    if fallos:
        print("\nEl entorno no esta listo:")
        for que, arreglo in fallos:
            print(f"- {que}\n  -> {arreglo}")
        return 1
    print(f"Entorno OK (Python {sys.version_info[0]}.{sys.version_info[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
