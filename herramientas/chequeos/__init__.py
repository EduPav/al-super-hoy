"""Chequeos deterministas sobre los archivos de instrucciones y documentacion.

Cada modulo devuelve `Resultado`: que paso, que fallo y que quedo sin evaluar.
Un chequeo que no se puede evaluar (por ejemplo, porque no hay arbol de git) se
reporta como omitido, nunca como aprobado: un verde que no midio nada es peor
que un rojo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Resultado:
    """Lo que devuelve cada chequeo."""

    pasaron: list[str] = field(default_factory=list)
    fallaron: list[str] = field(default_factory=list)
    omitidos: list[str] = field(default_factory=list)

    def anotar(self, condicion: bool, mensaje: str, detalle: str = "") -> bool:
        """Registra un chequeo. El detalle es obligatorio cuando se compara.

        Un fallo sin "esperaba X, encontre Y" obliga a leer el codigo del
        chequeo para entenderlo, que es justo lo que este repo evita.
        """
        if condicion:
            self.pasaron.append(mensaje)
            return True
        self.fallaron.append(f"{mensaje} — {detalle}" if detalle else mensaje)
        return False

    def omitir(self, mensaje: str) -> None:
        self.omitidos.append(mensaje)

    def sumar(self, otro: Resultado) -> Resultado:
        self.pasaron += otro.pasaron
        self.fallaron += otro.fallaron
        self.omitidos += otro.omitidos
        return self
