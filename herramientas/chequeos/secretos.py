"""Lo que el repo promete no publicar, git lo tiene que estar ignorando.

Este repo es publico y el historial queda aunque el archivo despues se borre,
asi que la regla "nunca commitear un .env" no puede vivir solo en la prosa.

Se le pregunta a git, no al texto del `.gitignore`: un patron escrito puede
estar tapado por otra regla, o vivir en un `.gitignore` que nadie versiono y que
en un clon nuevo no existe. Si no hay arbol de git, el chequeo se reporta como
omitido; un verde que no pudo medir nada es peor que un rojo.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import Resultado

# Rutas que git tiene que ignorar, con el motivo que se muestra al fallar.
IGNORADOS = {
    ".env": "credenciales; si alguna fuente las necesita, van a GitHub Secrets",
    "datos/cache/": "paginas de detalle descargadas; se regeneran solas",
}

# Nombres que nunca deberian estar versionados, por mas que git los ignore hoy.
PROHIBIDOS = (".env", ".env.local", ".env.production", "credenciales.json", "secrets.json")


def _git(raiz: Path, *argumentos: str) -> tuple[int, str]:
    try:
        salida = subprocess.run(
            ["git", *argumentos],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # git no instalado
        return 127, str(exc)
    return salida.returncode, salida.stdout


def hay_arbol_git(raiz: Path) -> bool:
    codigo, salida = _git(raiz, "rev-parse", "--is-inside-work-tree")
    return codigo == 0 and salida.strip() == "true"


def chequear(raiz: Path) -> Resultado:
    r = Resultado()
    if not hay_arbol_git(raiz):
        r.omitir("lo que git ignora (no hay arbol de git o git no esta instalado)")
        return r

    for ruta, motivo in IGNORADOS.items():
        codigo, _ = _git(raiz, "check-ignore", "-q", "--", ruta)
        if codigo not in (0, 1):
            r.omitir(f"si git ignora {ruta} (git no supo responder)")
            continue
        r.anotar(
            codigo == 0,
            f"git ignora {ruta}",
            f"esperaba que git ignorara {ruta} ({motivo}); hoy lo versionaria",
        )

    codigo, salida = _git(raiz, "ls-files")
    if codigo != 0:
        r.omitir("archivos prohibidos versionados (git ls-files fallo)")
        return r

    versionados = [linea.strip() for linea in salida.splitlines() if linea.strip()]
    for prohibido in PROHIBIDOS:
        encontrados = [v for v in versionados if Path(v).name == prohibido]
        r.anotar(
            not encontrados,
            f"no hay ningun {prohibido} versionado",
            f"esperaba ninguno, encontre {encontrados}; el historial de git lo conserva "
            "aunque se borre el archivo",
        )
    return r
