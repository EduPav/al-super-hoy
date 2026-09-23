"""Los limites del codigo, verificados en vez de solamente documentados.

Una regla de arquitectura que solo vive en un documento dura hasta el primer
cambio apurado. Estas pruebas son las que hacen que las capas de ARQUITECTURA.md
sean ciertas.
"""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path

import pytest
import yaml

from herramientas.chequeos.limites import CODIGO_MAX_LINEAS
from ingesta import fuentes

RAIZ = Path(__file__).resolve().parent.parent

# Las capas de la ingesta. Un modulo solo puede importar capas mas bajas que la
# suya; entre modulos de la misma carpeta si, porque son una sola pieza.
CAPAS = {"modelo": 0, "zona": 1, "fuentes": 2, "main": 3, "explorar": 3}

# La red vive en una sola capa. Si `requests` aparece en el orquestador o en el
# modelo, ya hay una llamada a internet donde no se la espera (y una prueba que
# no se puede escribir sin red).
LIBRERIAS_DE_RED = {"requests", "bs4", "urllib", "urllib3", "http"}

CODIGO = sorted(
    p
    for carpeta in ("ingesta", "herramientas", "pruebas")
    for p in (RAIZ / carpeta).rglob("*.py")
    if "__pycache__" not in p.parts
)
INGESTA = [p for p in CODIGO if p.relative_to(RAIZ).parts[0] == "ingesta"]


def _modulo(ruta: Path) -> str:
    relativo = ruta.relative_to(RAIZ).with_suffix("")
    partes = [p for p in relativo.parts if p != "__init__"]
    return ".".join(partes)


def _capa(modulo: str) -> int | None:
    partes = modulo.split(".")
    if partes[0] != "ingesta" or len(partes) < 2:
        return None
    return CAPAS.get(partes[1])


def _importados(ruta: Path) -> list[str]:
    """Modulos del propio paquete que importa este archivo, ya resueltos."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    propio = _modulo(ruta).split(".")
    # En un __init__.py, `from . import x` apunta al propio paquete; en un
    # modulo suelto apunta al paquete que lo contiene. Un salto de diferencia.
    propio_es_paquete = 1 if ruta.name == "__init__.py" else 0
    salida = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.level:
            base = propio[: len(propio) - nodo.level + propio_es_paquete]
            salida.append(".".join(base + ([nodo.module] if nodo.module else [])))
    return salida


@pytest.mark.parametrize("ruta", INGESTA, ids=_modulo)
def test_ningun_modulo_importa_una_capa_mas_alta(ruta: Path):
    propia = _capa(_modulo(ruta))
    if propia is None:
        pytest.skip("el archivo no pertenece a una capa de la ingesta")
    for importado in _importados(ruta):
        otra = _capa(importado)
        if otra is None or importado.startswith(_modulo(ruta).rsplit(".", 1)[0] + "."):
            continue
        assert otra <= propia, (
            f"{_modulo(ruta)} (capa {propia}) importa {importado} (capa {otra}): "
            "las capas van de modelo a main, nunca al reves"
        )


@pytest.mark.parametrize("ruta", INGESTA, ids=_modulo)
def test_la_red_solo_se_toca_en_la_capa_de_fuentes(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    importadas = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importadas |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and not nodo.level and nodo.module:
            importadas.add(nodo.module.split(".")[0])

    culpables = importadas & LIBRERIAS_DE_RED
    esta_en_fuentes = "fuentes" in ruta.relative_to(RAIZ).parts
    assert not culpables or esta_en_fuentes, (
        f"{_modulo(ruta)} importa {sorted(culpables)}; la red solo se toca en ingesta/fuentes/"
    )


@pytest.mark.parametrize("ruta", CODIGO, ids=_modulo)
def test_los_archivos_entran_en_una_lectura(ruta: Path):
    lineas = len(ruta.read_text(encoding="utf-8").splitlines())
    assert lineas <= CODIGO_MAX_LINEAS, (
        f"{_modulo(ruta)} tiene {lineas} lineas y el limite es {CODIGO_MAX_LINEAS}: "
        "partilo en una pieza con red y otra pura, como modo.py y modo_traduccion.py"
    )


def _modulos_de_fuente() -> list[str]:
    """Modulos de ingesta/fuentes/ con `listar`: esos, y solo esos, son fuentes.

    Se importan de verdad en vez de leerlos con ast: importar una fuente no
    abre ninguna conexion (la red recien se toca dentro de `listar`), y asi el
    contrato se verifica sobre lo que el orquestador va a encontrar, no sobre
    la forma en que el archivo esta escrito.
    """
    encontrados = []
    for ruta in sorted((RAIZ / "ingesta" / "fuentes").glob("*.py")):
        if ruta.name == "__init__.py":
            continue
        modulo = import_module(f"ingesta.fuentes.{ruta.stem}")
        if callable(getattr(modulo, "listar", None)):
            encontrados.append(ruta.stem)
    return encontrados


def test_hay_fuentes_declaradas():
    assert _modulos_de_fuente(), "ningun modulo define listar(): el contrato quedo vacio"


@pytest.mark.parametrize("nombre", _modulos_de_fuente())
def test_cada_fuente_cumple_el_contrato(nombre: str):
    modulo = import_module(f"ingesta.fuentes.{nombre}")

    assert isinstance(getattr(modulo, "NOMBRE", None), str) and modulo.NOMBRE, (
        f"{nombre} no expone NOMBRE; ese es el texto que ve el usuario en la "
        "pestana Fuentes y no puede estar escrito dos veces"
    )
    assert getattr(modulo, "ErrorFuente", None) is fuentes.ErrorFuente, (
        f"{nombre} no usa el ErrorFuente compartido; el orquestador degrada fuente "
        "por fuente atrapando ese tipo, y una excepcion propia se le escapa"
    )


def test_el_user_agent_se_declara_una_sola_vez():
    # Identificarse es parte del trato con una fuente publica. Dos copias del
    # User-Agent significan que una va a quedar vieja o vacia.
    con_user_agent = [
        p for p in (RAIZ / "ingesta").rglob("*.py")
        if "User-Agent" in p.read_text(encoding="utf-8")
    ]
    assert [p.name for p in con_user_agent] == ["__init__.py"], (
        f"el User-Agent aparece en {[p.name for p in con_user_agent]}; "
        "va una sola vez, en ingesta/fuentes/__init__.py"
    )


def test_el_registro_de_comercios_es_valido():
    datos = yaml.safe_load((RAIZ / "datos" / "comercios-santa-fe.yml").read_text(encoding="utf-8"))
    comercios = datos.get("comercios") or []
    assert comercios, "el registro esta vacio: sin el no hay filtro de zona"

    nombres = [c.get("nombre", "").strip() for c in comercios]
    assert all(nombres), "hay un comercio sin nombre en el registro"
    assert len(set(nombres)) == len(nombres), (
        f"hay nombres repetidos: {sorted({n for n in nombres if nombres.count(n) > 1})}"
    )
    for comercio in comercios:
        assert isinstance(comercio.get("confirmado", True), bool), (
            f"{comercio.get('nombre')}: `confirmado` tiene que ser true o false"
        )
