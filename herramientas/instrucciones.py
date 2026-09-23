"""Chequeo de la superficie de instrucciones. Sin dependencias, a proposito.

`python -m herramientas.instrucciones`

AGENTS.md es la unica fuente de instrucciones del repo. Este chequeo verifica
que siga siendo legible (tamano), que conserve las reglas que no se negocian
(autoridad de las instrucciones, manejo de secretos), que CLAUDE.md siga siendo
un puntero y no una segunda copia, que los links y anclas resuelvan, que los
comandos documentados existan y que CI corra los que dice correr.

Usa solo la biblioteca estandar para que corra en un clon recien bajado, antes
de instalar nada: es el primer gate y no puede depender de que el entorno este
armado.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .chequeos import Resultado, enlaces, secretos
from .chequeos import comandos as chequeo_comandos
from .chequeos import limites as lim
from .chequeos.markdown import prohibe, seccion, titulos

RAIZ = Path(__file__).resolve().parent.parent

# Documentos que tienen que existir y no pueden estar vacios. LICENSE y
# CONTRIBUTING.md estan aca porque el repo es publico: sin licencia nadie puede
# forkearlo aunque lo lea, y sin CONTRIBUTING no hay camino de entrada.
OBLIGATORIOS = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "ARQUITECTURA.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "documentacion/verificacion.md",
    "documentacion/flujos-de-trabajo.md",
    "documentacion/seguridad.md",
)

# Secciones de AGENTS.md que cargan una regla. Si una desaparece, la regla se
# perdio aunque el archivo siga existiendo. Sin acentos: el patron se compara
# contra el titulo ya normalizado.
SECCIONES = (
    r"autoridad de las instrucciones",
    r"manejo de secretos",
    r"comandos",
    r"control mecanico",
    r"donde se documenta cada cambio",
    r"mapa de documentos",
)

PUNTEROS = ("CLAUDE.md",)

FECHA = re.compile(r"<!--\s*ultima_verificacion:\s*(\d{4}-\d{2}-\d{2}|AAAA-MM-DD)\s*-->")
PRUEBA_CITADA = re.compile(r"(pruebas/test_[\w]+\.py)::(test_[\w]+)")


def _leer(r: Resultado, relativo: str) -> str | None:
    """Contenido del archivo, o None si falta o esta vacio: ambos son fallos."""
    ruta = RAIZ / relativo
    if not r.anotar(ruta.exists(), f"{relativo} existe", f"esperaba un archivo en {relativo}"):
        return None
    texto = ruta.read_text(encoding="utf-8")
    if not r.anotar(
        texto.strip() != "",
        f"{relativo} no esta vacio",
        f"esperaba contenido, encontre {len(texto)} bytes",
    ):
        return None
    return texto


def _agents(r: Resultado, texto: str) -> None:
    tamano = (RAIZ / "AGENTS.md").stat().st_size
    lineas = len(texto.rstrip().splitlines())

    r.anotar(
        tamano >= lim.AGENTS_MIN_BYTES,
        "AGENTS.md no quedo sospechosamente corto",
        f"esperaba >= {lim.AGENTS_MIN_BYTES} bytes, tiene {tamano}",
    )
    r.anotar(
        tamano <= lim.AGENTS_MAX_BYTES,
        f"AGENTS.md se mantiene bajo {lim.AGENTS_MAX_BYTES} bytes",
        f"esperaba <= {lim.AGENTS_MAX_BYTES} bytes, tiene {tamano}",
    )
    r.anotar(
        lineas <= lim.AGENTS_MAX_LINEAS,
        f"AGENTS.md se mantiene bajo {lim.AGENTS_MAX_LINEAS} lineas",
        f"esperaba <= {lim.AGENTS_MAX_LINEAS} lineas, tiene {lineas}; "
        "el detalle va en documentacion/, no aca",
    )

    for patron in SECCIONES:
        r.anotar(
            seccion(texto, patron) is not None,
            f"AGENTS.md conserva la seccion '{patron}'",
            f"esperaba un titulo de nivel 2 a 4 que coincida con '{patron}'",
        )

    _autoridad(r, texto)
    _secretos(r, texto)
    _pruebas_citadas(r, texto)


def _autoridad(r: Resultado, texto: str) -> None:
    """La frontera de confianza: que manda y que es solo un dato leido."""
    cuerpo = seccion(texto, r"autoridad de las instrucciones")
    if cuerpo is None:
        return
    plano = cuerpo.lower()

    r.anotar(
        "pedido" in plano and ("agents.md" in plano or "este archivo" in plano),
        "AGENTS.md declara quien tiene autoridad sobre el trabajo",
        "esperaba que la seccion nombre el pedido del usuario y las instrucciones "
        f"del repo como lo que manda; texto actual: {cuerpo.strip()[:200]!r}",
    )

    # Este repo lee paginas y APIs de terceros: el riesgo no es teorico.
    for etiqueta, agujas in (
        ("las paginas y respuestas que scrapea", ["html", "pagina", "api", "respuesta"]),
        ("los issues y comentarios", ["issue", "comentario"]),
    ):
        r.anotar(
            any(a in plano for a in agujas)
            and ("dato" in plano or "no son instrucciones" in plano),
            f"AGENTS.md trata {etiqueta} como datos, no como instrucciones",
            f"esperaba que la seccion nombre {agujas} y aclare que son datos; "
            f"texto actual: {cuerpo.strip()[:200]!r}",
        )


def _secretos(r: Resultado, texto: str) -> None:
    cuerpo = seccion(texto, r"manejo de secretos")
    if cuerpo is None:
        return
    for etiqueta, agujas in (
        ("los archivos .env", [".env", "archivo de entorno"]),
        ("las credenciales", ["credencial", "contrasena", "cookie"]),
        ("las claves de API", ["api key", "clave de api", "token"]),
        ("mostrarlas o imprimirlas", ["imprim", "mostrar", "pegar", "publicar"]),
        ("las superficies de fuga", ["log", "captura", "commit", "chat", "reporte"]),
    ):
        r.anotar(
            prohibe(cuerpo, agujas),
            f"la regla de secretos prohibe {etiqueta}",
            f"esperaba alguno de {agujas} en el mismo enunciado que una prohibicion "
            f"(nunca / no / jamas); texto actual: {cuerpo.strip()[:300]!r}",
        )


def _pruebas_citadas(r: Resultado, texto: str) -> None:
    """Cada prueba que AGENTS.md nombra como control tiene que existir."""
    citadas = set(PRUEBA_CITADA.findall(texto))
    r.anotar(
        bool(citadas),
        "la tabla de control mecanico cita pruebas concretas",
        "esperaba al menos una referencia con la forma pruebas/test_x.py::test_y",
    )
    for archivo, prueba in sorted(citadas):
        ruta = RAIZ / archivo
        if not r.anotar(
            ruta.exists(),
            f"la prueba citada {archivo} existe",
            f"AGENTS.md la nombra como control, no hay archivo en {archivo}",
        ):
            continue
        r.anotar(
            re.search(rf"^def {prueba}\b", ruta.read_text(encoding="utf-8"), re.MULTILINE)
            is not None,
            f"{archivo} define {prueba}",
            f"AGENTS.md dice que {prueba} controla una regla; esa funcion no esta en {archivo}",
        )


def _punteros(r: Resultado) -> None:
    """CLAUDE.md apunta a AGENTS.md; nunca repite las reglas."""
    for relativo in PUNTEROS:
        ruta = RAIZ / relativo
        if not r.anotar(
            ruta.exists(), f"{relativo} existe", f"esperaba un puntero a AGENTS.md en {relativo}"
        ):
            continue
        texto = ruta.read_text(encoding="utf-8")
        tamano = ruta.stat().st_size
        lineas = len(texto.rstrip().splitlines())
        r.anotar(
            "AGENTS.md" in texto,
            f"{relativo} apunta a AGENTS.md",
            f"esperaba el texto 'AGENTS.md', contenido actual: {texto.strip()[:200]!r}",
        )
        r.anotar(
            tamano <= lim.PUNTERO_MAX_BYTES and lineas <= lim.PUNTERO_MAX_LINEAS,
            f"{relativo} sigue siendo un puntero",
            f"esperaba <= {lim.PUNTERO_MAX_BYTES} bytes y <= {lim.PUNTERO_MAX_LINEAS} lineas, "
            f"tiene {tamano} bytes y {lineas} lineas; si crecio, ya es una segunda copia "
            "de las reglas",
        )


def _ancla_secretos(r: Resultado, agents: str, seguridad: str) -> None:
    """seguridad.md no repite la regla de secretos: apunta a la unica."""
    anclas = re.findall(r"\(\.\./AGENTS\.md#([\w-]+)\)", seguridad)
    if not r.anotar(
        bool(anclas),
        "documentacion/seguridad.md entra a AGENTS.md por ancla",
        "esperaba un link con la forma (../AGENTS.md#manejo-de-secretos); no hay ninguno",
    ):
        return
    titulo = next((t for t in titulos(agents) if "secretos" in t.texto.lower()), None)
    r.anotar(
        titulo is not None and titulo.ancla in anclas,
        "el ancla de seguridad.md resuelve al titulo de secretos de AGENTS.md",
        f"esperaba un link a #{titulo.ancla if titulo else '???'}, "
        f"seguridad.md apunta a {anclas}",
    )


def _fechas(r: Resultado) -> None:
    """Cada documento declara cuando se verifico por ultima vez."""
    fechados = [RAIZ / "AGENTS.md", RAIZ / "ARQUITECTURA.md"]
    fechados += sorted((RAIZ / "documentacion").rglob("*.md"))
    hoy = date.today().isoformat()
    for ruta in fechados:
        if not ruta.exists():
            continue
        relativo = ruta.relative_to(RAIZ).as_posix()
        encontrado = FECHA.search(ruta.read_text(encoding="utf-8")[:400])
        if not r.anotar(
            encontrado is not None,
            f"{relativo} declara su ultima verificacion",
            "esperaba un <!-- ultima_verificacion: AAAA-MM-DD --> en el encabezado",
        ):
            continue
        valor = encontrado.group(1)
        if valor == "AAAA-MM-DD":  # plantilla sin completar
            continue
        r.anotar(
            valor <= hoy,
            f"{relativo} no se verifico en el futuro",
            f"esperaba una fecha <= {hoy}, dice {valor}",
        )


def chequear() -> Resultado:
    r = Resultado()
    textos = {relativo: _leer(r, relativo) for relativo in OBLIGATORIOS}

    agents = textos.get("AGENTS.md")
    if agents:
        _agents(r, agents)
        companeros = {
            nombre: textos[nombre] or ""
            for nombre in ("README.md", "documentacion/flujos-de-trabajo.md")
        }
        r.sumar(chequeo_comandos.chequear(RAIZ, agents, companeros))
        if textos.get("documentacion/seguridad.md"):
            _ancla_secretos(r, agents, textos["documentacion/seguridad.md"])

    _punteros(r)
    _fechas(r)
    r.sumar(enlaces.chequear(RAIZ))
    r.sumar(secretos.chequear(RAIZ))
    return r


def main() -> int:
    r = chequear()
    for omitido in r.omitidos:
        print(f"OMITIDO: {omitido}")
    if r.fallaron:
        print("\nEl chequeo de instrucciones fallo:")
        for fallo in r.fallaron:
            print(f"- {fallo}")
        return 1
    extra = f", {len(r.omitidos)} omitidos" if r.omitidos else ""
    print(f"Chequeo de instrucciones OK ({len(r.pasaron)} chequeos{extra})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
