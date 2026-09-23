"""Lectura de markdown que respeta los bloques de codigo.

Un `# comando` dentro de un bloque ``` no es un titulo. Si se lo cuenta como
titulo, el cuerpo de la seccion anterior se corta ahi y el chequeo de esa
seccion pasa a mirar un texto vacio: un verde que no midio nada.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CERCA = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
TITULO = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Titulo:
    linea: int
    nivel: int
    texto: str
    ancla: str


def sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def ancla(texto: str) -> str:
    """Ancla al estilo GitHub: `## 3. Manejo de secretos` -> `3-manejo-de-secretos`.

    Cada espacio da su propio guion, como hace GitHub. Colapsar los espacios
    inventa anclas que GitHub no sirve, y entonces un link que funciona en el
    navegador falla en el chequeo.
    """
    limpio = re.sub(r"[^\w\s-]", "", texto.lower(), flags=re.UNICODE)
    return re.sub(r"\s", "-", limpio)


def titulos(texto: str) -> list[Titulo]:
    """Titulos de prosa, en orden. Los de adentro de un bloque no cuentan."""
    encontrados: list[Titulo] = []
    cerca: str | None = None
    for i, linea in enumerate(texto.splitlines()):
        marca = CERCA.match(linea)
        if marca:
            simbolo = marca.group(1)[0]
            # Una cerca solo la cierra el mismo caracter que la abrio.
            cerca = None if cerca == simbolo else (cerca or simbolo)
            continue
        if cerca is not None:
            continue
        hallado = TITULO.match(linea)
        if hallado:
            crudo = hallado.group(2).strip()
            encontrados.append(Titulo(i, len(hallado.group(1)), crudo, ancla(crudo)))
    return encontrados


def seccion(texto: str, patron: str, nivel_max: int = 4) -> str | None:
    """Cuerpo de la primera seccion cuyo titulo coincide con `patron`.

    Se busca por el texto del titulo y sin acentos, no por su numero: la
    numeracion se mueve cada vez que se agrega una seccion, y la regla no.
    """
    lineas = texto.splitlines()
    todos = titulos(texto)
    regex = re.compile(patron, re.IGNORECASE)
    indice = next(
        (
            i
            for i, t in enumerate(todos)
            if 2 <= t.nivel <= nivel_max and regex.search(sin_acentos(t.texto))
        ),
        None,
    )
    if indice is None:
        return None
    siguiente = next((t for t in todos[indice + 1:] if t.nivel <= nivel_max), None)
    fin = siguiente.linea if siguiente else len(lineas)
    return "\n".join(lineas[todos[indice].linea + 1:fin])


def _desenvolver(cuerpo: str) -> str:
    """Une las lineas de continuacion de un item de lista o de un parrafo.

    Un item de markdown se corta a los 80 caracteres y sigue indentado abajo.
    Si cada linea contara como un enunciado, una regla que nombra la cosa en
    una linea y la prohibicion en la anterior quedaria partida en dos y el
    chequeo la daria por incumplida.
    """
    lineas: list[str] = []
    for linea in cuerpo.splitlines():
        continua = lineas and lineas[-1].strip() and linea.strip() and linea[:1].isspace()
        if continua:
            lineas[-1] += " " + linea.strip()
        else:
            lineas.append(linea)
    return "\n".join(lineas)


def enunciados(cuerpo: str) -> list[str]:
    """Parte un cuerpo en enunciados: items de lista y oraciones."""
    plano = _desenvolver(cuerpo)
    return [p.strip() for p in re.split(r"\r?\n|(?<=[.!?;])\s+", plano) if p.strip()]


PROHIBICION = re.compile(
    r"\bnunca\b|\bno\b|\bjamas\b|\bprohibid|\bevita", re.IGNORECASE
)


def prohibe(cuerpo: str, agujas: list[str]) -> bool:
    """True si un mismo enunciado nombra algo de `agujas` y lo prohibe.

    Que sea el *mismo* enunciado es el punto: con dos frases sueltas, una
    oracion que dice lo contrario alcanzaba para dar por cumplida la regla.
    """
    for parte in enunciados(cuerpo):
        plano = sin_acentos(parte).lower()
        if PROHIBICION.search(plano) and any(a in plano for a in agujas):
            return True
    return False


def bloques_codigo(texto: str, lenguaje: str = "") -> list[str]:
    """Contenido de los bloques cercados, opcionalmente filtrando por lenguaje."""
    bloques: list[str] = []
    actual: list[str] | None = None
    cerca: str | None = None
    for linea in texto.splitlines():
        marca = CERCA.match(linea)
        if marca:
            simbolo = marca.group(1)[0]
            if cerca is None:
                cerca = simbolo
                etiqueta = linea.strip().lstrip("`~").strip().lower()
                actual = [] if (not lenguaje or etiqueta == lenguaje) else None
            elif cerca == simbolo:
                if actual is not None:
                    bloques.append("\n".join(actual))
                cerca, actual = None, None
            continue
        if actual is not None:
            actual.append(linea)
    return bloques


def sin_codigo(texto: str) -> list[str]:
    """Lineas con el codigo en blanco, conservando la numeracion original."""
    salida: list[str] = []
    cerca: str | None = None
    for linea in texto.splitlines():
        marca = CERCA.match(linea)
        if marca:
            simbolo = marca.group(1)[0]
            cerca = None if cerca == simbolo else (cerca or simbolo)
            salida.append("")
            continue
        salida.append("" if cerca is not None else re.sub(r"`+[^`\n]*`+", "", linea))
    return salida
