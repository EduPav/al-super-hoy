"""Los comandos que la documentacion nombra existen, y CI corre los que dice.

Tres formas de mentir que este chequeo cierra:

1. Documentar un comando que ya no existe (se renombro el modulo).
2. Nombrar el gate en AGENTS.md y olvidarlo en el README o en los flujos, donde
   la proxima persona lo va a buscar.
3. Decir que CI lo corre cuando el workflow ya no lo corre.

El tercero es el que mas cuesta ver. Por eso `run:` se reconoce solo a nivel de
paso: un `run` que es un input dentro de `with:`, o texto dentro de un bloque
`run: |`, no ejecuta nada y no alcanza para cumplir "CI corre X".
"""

from __future__ import annotations

import re
from pathlib import Path

from . import Resultado
from .markdown import bloques_codigo, seccion

# Un comando marcado `# [CI] ...` en la seccion Comandos de AGENTS.md declara
# que CI lo corre. El marcador vive en AGENTS.md y no aca: asi el chequeo no
# guarda una tercera copia de la lista de gates.
MARCA_CI = "[CI]"

PY_MODULO = re.compile(r"python\s+-m\s+([\w.]+)")
PIP_REQS = re.compile(r"pip\s+install\s+-r\s+(\S+)")
# Modulos de la biblioteca estandar que la documentacion usa como herramienta.
STDLIB = {"http.server", "pip", "venv", "pytest", "ruff"}


def comandos_documentados(agents: str) -> list[tuple[str, bool]]:
    """Comandos de la seccion Comandos, con su marca de "lo corre CI"."""
    cuerpo = seccion(agents, r"comandos")
    if cuerpo is None:
        return []
    salida: list[tuple[str, bool]] = []
    for bloque in bloques_codigo(cuerpo, "bash"):
        for linea in bloque.splitlines():
            comando, _, comentario = linea.partition("#")
            comando = comando.strip()
            if comando:
                salida.append((comando, MARCA_CI in comentario))
    return salida


def _modulo_existe(raiz: Path, modulo: str) -> bool:
    if modulo in STDLIB:
        return True
    ruta = raiz / Path(*modulo.split("."))
    return ruta.with_suffix(".py").exists() or (ruta / "__init__.py").exists()


def pasos_run(workflow: str) -> list[str]:
    """Comandos declarados en un `run:` a nivel de paso.

    No cuenta un `run` que sea clave anidada (por ejemplo un input de `with:`)
    ni el contenido de un bloque `run: |`, que ya fue consumido con su paso.
    """
    lineas = workflow.splitlines()
    salida: list[str] = []
    steps_indent: int | None = None
    item_indent: int | None = None
    cuerpo_indent: int | None = None
    i = 0

    while i < len(lineas):
        linea = lineas[i]
        i += 1
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        indent = len(linea) - len(linea.lstrip())

        if re.match(r"^\s*steps:\s*(#.*)?$", linea):
            steps_indent, item_indent, cuerpo_indent = indent, None, None
            continue
        if steps_indent is None:
            continue
        if indent <= steps_indent:  # se termino el bloque steps de este job
            steps_indent = item_indent = cuerpo_indent = None
            continue

        item = re.match(r"^(\s*)-\s+(\S.*)$", linea)
        if item and (item_indent is None or indent == item_indent):
            item_indent = indent
            cuerpo_indent = indent + 2
            resto, desplazamiento = item.group(2), cuerpo_indent
        elif cuerpo_indent is not None and indent == cuerpo_indent:
            resto, desplazamiento = linea.strip(), cuerpo_indent
        else:
            continue

        clave = re.match(r"^run:\s*(.*)$", resto)
        if not clave:
            continue
        valor = clave.group(1).strip()
        if valor.startswith(("|", ">")):
            # Bloque: todo lo mas indentado que la clave es su contenido, y se
            # consume aca para que el bucle no lo vuelva a leer como si fueran
            # lineas de nivel de paso.
            while i < len(lineas):
                siguiente = lineas[i]
                if siguiente.strip() and (
                    len(siguiente) - len(siguiente.lstrip())
                ) <= desplazamiento:
                    break
                salida.append(siguiente.strip())
                i += 1
        elif valor:
            salida.append(valor)

    return [c for c in salida if c and not c.startswith("#")]


def corre(corridos: list[str], gate: str) -> bool:
    """True si alguno de los comandos corridos ES el gate.

    Por inicio de linea y no por subcadena: una linea de datos dentro de un
    heredoc (`run: python -m ...` escrito adentro de un `cat <<FIN`) contiene
    el texto del gate y no ejecuta nada.
    """
    return any(c == gate or c.startswith(gate + " ") for c in corridos)


def chequear(raiz: Path, agents: str, companeros: dict[str, str]) -> Resultado:
    r = Resultado()
    comandos = comandos_documentados(agents)

    if not r.anotar(
        bool(comandos),
        "AGENTS.md documenta sus comandos en un bloque bash",
        "esperaba una seccion 'Comandos' con al menos un bloque ```bash",
    ):
        return r

    for comando, _ in comandos:
        modulo = PY_MODULO.search(comando)
        if modulo:
            r.anotar(
                _modulo_existe(raiz, modulo.group(1)),
                f"el comando `{comando}` apunta a un modulo que existe",
                f"esperaba encontrar el modulo {modulo.group(1)} en el repo, no esta",
            )
        reqs = PIP_REQS.search(comando)
        if reqs:
            r.anotar(
                (raiz / reqs.group(1)).exists(),
                f"el comando `{comando}` apunta a un archivo que existe",
                f"esperaba {reqs.group(1)} en la raiz del repo, no esta",
            )

    gates = [c for c, ci in comandos if ci]
    r.anotar(
        bool(gates),
        f"AGENTS.md marca con {MARCA_CI} los comandos que corre CI",
        f"esperaba al menos un comando con el marcador {MARCA_CI} en su comentario",
    )

    # Los gates se nombran donde la gente los busca, no solo en AGENTS.md.
    for nombre, texto in companeros.items():
        for gate in gates:
            r.anotar(
                gate in texto,
                f"{nombre} nombra el gate `{gate}`",
                f"esperaba el texto literal `{gate}` en {nombre}",
            )

    return r.sumar(_chequear_ci(raiz, gates))


def _chequear_ci(raiz: Path, gates: list[str]) -> Resultado:
    r = Resultado()
    directorio = raiz / ".github" / "workflows"
    if not directorio.is_dir():
        r.omitir("lo que corre CI (no hay .github/workflows)")
        return r

    corridos: list[str] = []
    for workflow in sorted(directorio.glob("*.yml")) + sorted(directorio.glob("*.yaml")):
        texto = workflow.read_text(encoding="utf-8")
        # Un job apagado sigue "declarando" el paso: satisface una busqueda por
        # texto y no ejecuta nada.
        r.anotar(
            not re.search(r"^\s*if:\s*(false|\$\{\{\s*false\s*\}\})\s*$", texto, re.MULTILINE),
            f"{workflow.name} no tiene jobs ni pasos apagados con `if: false`",
            "esperaba ningun `if: false`; un job apagado deja el gate sin correr",
        )
        corridos += pasos_run(texto)

    for gate in gates:
        r.anotar(
            corre(corridos, gate),
            f"CI corre el gate `{gate}`",
            f"esperaba un paso con `run:` que invoque `{gate}`; "
            f"lo que CI corre hoy: {corridos}",
        )
    return r
