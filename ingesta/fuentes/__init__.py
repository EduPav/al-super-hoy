"""Acceso a las fuentes publicas. Es la unica capa que habla por la red.

Cada modulo de fuente cumple el mismo contrato, y `pruebas/test_estructura.py`
lo verifica:

- declara `NOMBRE`, la etiqueta que ve el usuario en la pestana Fuentes;
- expone `listar(sesion=None)`, que devuelve lo que la fuente publica hoy;
- ante cualquier fallo de red o de formato levanta `ErrorFuente`, nunca una
  excepcion de la libreria HTTP. El orquestador degrada esa fuente y sigue con
  las demas.

Los modulos auxiliares sin `listar` (por ejemplo `modo_traduccion`) no son
fuentes: son funciones puras, sin red, y por eso se pueden probar solas.
"""

from __future__ import annotations

import requests

# Alias para que el orquestador pueda tipar la sesion sin importar requests:
# la libreria HTTP no sale de esta capa.
Sesion = requests.Session

# Identificarse es parte del trato con una fuente publica: quien golpea, para
# que, y un canal para pedir que pare. Una sola vez, para todas las fuentes.
CABECERAS = {
    "User-Agent": (
        "al-super-hoy/1.0 (uso personal; lector de promociones publicas; "
        "https://github.com/EduPav/al-super-hoy)"
    ),
    "Accept": "application/json, text/html",
}


class ErrorFuente(Exception):
    """La fuente no pudo leerse. El orquestador decide si degrada o aborta."""


def sesion() -> Sesion:
    """Sesion HTTP compartida, ya identificada con el User-Agent del proyecto."""
    s = requests.Session()
    s.headers.update(CABECERAS)
    return s
