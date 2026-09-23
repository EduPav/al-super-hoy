"""Filtro geografico: que promos son relevantes para Santa Fe capital.

La API de MODO es nacional y no publica las sucursales de cada promo, asi que
la relevancia no se puede deducir de los datos: hay que declararla. Este modulo
lee el registro curado de `datos/comercios-santa-fe.yml` y decide que entra.

Los comercios que no reconoce no se descartan en silencio: quedan anotados para
que se puedan revisar y sumar al registro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .modelo import Promo, clave

REGISTRO = Path(__file__).resolve().parent.parent / "datos" / "comercios-santa-fe.yml"


def contiene(patron: str, texto: str) -> bool:
    """True si `patron` aparece en `texto` como secuencia de palabras completas.

    Comparar por subcadena suelta mezcla comercios distintos: "dia" aparece
    dentro de "diarco", "diamante" y "cordial", y "vea" dentro de "alvear".
    Exigir palabras completas y contiguas evita esos falsos positivos.

    La direccion importa: el nombre del registro tiene que estar dentro del
    nombre de la promo, no al reves. Asi "Carrefour" reconoce a "Carrefour
    Express", pero "Carrefour Market" no se queda con un "Super Market"
    cualquiera.
    """
    if not patron or not texto:
        return False
    aguja, pajar = patron.split(), texto.split()
    if len(aguja) > len(pajar):
        return False
    return any(
        pajar[i:i + len(aguja)] == aguja
        for i in range(len(pajar) - len(aguja) + 1)
    )


@dataclass
class Comercio:
    nombre: str
    claves: set[str] = field(default_factory=set)
    confirmado: bool = True


class Zona:
    """Decide si una promo corresponde a un comercio de la zona."""

    def __init__(self, comercios: list[Comercio], descartados: set[str]):
        self.comercios = comercios
        self.descartados = descartados
        self.desconocidos: dict[str, int] = {}

    @classmethod
    def cargar(cls, ruta: Path | None = None) -> Zona:
        datos = yaml.safe_load((ruta or REGISTRO).read_text(encoding="utf-8")) or {}
        comercios = []
        for entrada in datos.get("comercios") or []:
            nombre = entrada.get("nombre", "").strip()
            if not nombre:
                continue
            claves = {clave(nombre)} | {clave(a) for a in entrada.get("alias") or []}
            comercios.append(
                Comercio(
                    nombre=nombre,
                    claves={c for c in claves if c},
                    confirmado=bool(entrada.get("confirmado", True)),
                )
            )
        descartados = {clave(d) for d in datos.get("descartados") or [] if clave(d)}
        return cls(comercios, descartados)

    def _buscar(self, comercio_clave: str) -> Comercio | None:
        if not comercio_clave:
            return None
        for c in self.comercios:
            if any(contiene(k, comercio_clave) for k in c.claves):
                return c
        return None

    def incluye(self, promo: Promo) -> bool:
        """True si la promo aplica en la zona. Registra los nombres nuevos."""
        encontrado = self._buscar(promo.comercio_clave)
        if encontrado:
            # Unificamos el nombre para que la app no muestre "ChangoMas" y
            # "ChangoMás" como si fueran dos comercios distintos.
            promo.comercio = encontrado.nombre
            promo.comercio_clave = clave(encontrado.nombre)
            return True
        if not self._descartado(promo.comercio_clave):
            self.desconocidos[promo.comercio] = self.desconocidos.get(promo.comercio, 0) + 1
        return False

    def _descartado(self, comercio_clave: str) -> bool:
        return any(contiene(d, comercio_clave) for d in self.descartados)

    def filtrar(self, promos: list[Promo]) -> list[Promo]:
        return [p for p in promos if self.incluye(p)]

    def por_confirmar(self) -> list[str]:
        """Comercios del registro que todavia no verificaste que existan."""
        return [c.nombre for c in self.comercios if not c.confirmado]

    def informe_desconocidos(self, limite: int = 40) -> list[dict]:
        """Comercios vistos en las promos que no estan en el registro."""
        ordenados = sorted(self.desconocidos.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{"comercio": n, "promos": c} for n, c in ordenados[:limite]]
