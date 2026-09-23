"""Las pruebas no tocan la red. Nunca.

Sin este candado, una prueba que "pasa" puede estar pidiendole las promos a
MODO: anda en una maquina con internet, falla en CI, y cuando MODO cambia algo
falla un cambio que no tiene nada que ver. Ademas golpear una fuente publica
cada vez que alguien corre las pruebas no es parte del trato.

El bloqueo es de sockets, no de `requests`: asi tambien queda cerrada cualquier
libreria que se agregue despues.
"""

from __future__ import annotations

import socket

import pytest

_conectar = socket.socket.connect
_crear = socket.create_connection


class RedProhibida(RuntimeError):
    """Una prueba intento salir a la red."""


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    def bloquear(*argumentos, **nombrados):
        raise RedProhibida(
            "las pruebas no abren sockets: usa una sesion falsa o un fixture "
            "de pruebas/fixtures/ en vez de llamar a la fuente real"
        )

    monkeypatch.setattr(socket.socket, "connect", bloquear)
    monkeypatch.setattr(socket, "create_connection", bloquear)
    yield
    monkeypatch.setattr(socket.socket, "connect", _conectar)
    monkeypatch.setattr(socket, "create_connection", _crear)
