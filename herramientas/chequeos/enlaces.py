"""Integridad de los links internos de la documentacion.

Cada link relativo se resuelve contra el disco, y cada `#ancla` contra los
titulos reales del archivo apuntado. Partir un documento rompe las anclas que
apuntaban a el sin que se note: GitHub sirve el archivo igual y deja al lector
arriba de todo, asi que el link roto se lee como si funcionara.

Los links externos (http, mailto) no se abren nunca: este chequeo corre sin red
y tiene que dar siempre lo mismo.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import Resultado
from .markdown import sin_codigo, titulos

# `](destino)`, tolerando un "titulo" opcional y un destino entre <>.
LINK = re.compile(r"\]\(\s*<?([^)>\s]+)>?(?:\s+[^)]*)?\)")

# Arboles generados o ajenos: ahi no hay documentacion escrita a mano.
OMITIR = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}


def documentos(raiz: Path) -> list[Path]:
    """Markdown del repo, en orden estable para que los fallos no bailen."""
    encontrados = [
        p
        for p in sorted(raiz.rglob("*.md"))
        if not any(parte in OMITIR for parte in p.relative_to(raiz).parts)
    ]
    return encontrados


def _anclas(archivo: Path) -> set[str]:
    return {t.ancla for t in titulos(archivo.read_text(encoding="utf-8"))}


def chequear(raiz: Path) -> Resultado:
    r = Resultado()
    cache: dict[Path, set[str]] = {}
    revisados = 0

    for doc in documentos(raiz):
        relativo = doc.relative_to(raiz).as_posix()
        for numero, linea in enumerate(sin_codigo(doc.read_text(encoding="utf-8")), start=1):
            for destino in LINK.findall(linea):
                if destino.startswith(("http://", "https://", "mailto:", "data:")):
                    continue
                ruta, _, ancla = destino.partition("#")
                origen = f"{relativo}:{numero}"

                if not ruta:  # link a una seccion del mismo archivo
                    objetivo = doc
                else:
                    objetivo = (doc.parent / ruta).resolve()
                    if not r.anotar(
                        objetivo.exists(),
                        f"{origen} apunta a un archivo que existe",
                        f"esperaba {ruta}, no hay nada en esa ruta",
                    ):
                        continue
                revisados += 1

                if not ancla or objetivo.suffix.lower() != ".md":
                    continue
                if objetivo not in cache:
                    cache[objetivo] = _anclas(objetivo)
                r.anotar(
                    ancla.lower() in cache[objetivo],
                    f"{origen} apunta a una seccion que existe",
                    f"esperaba un titulo con ancla #{ancla} en {ruta or relativo}, "
                    f"anclas reales: {sorted(cache[objetivo])}",
                )

    if revisados == 0:
        r.omitir("links internos (no se encontro ningun link relativo que revisar)")
    return r
