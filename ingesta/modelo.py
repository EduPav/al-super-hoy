"""Modelo canonico de promocion y utilidades de normalizacion.

Todas las fuentes se traducen a este modelo antes de fusionarse, de modo que el
frontend consume una sola forma de dato sin importar de donde salio.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone

# MODO codifica los dias con la inicial castellana. El indice coincide con
# datetime.weekday() (lunes = 0), asi que sirve para resolver "que aplica hoy".
DIAS = ["L", "M", "X", "J", "V", "S", "D"]

DIAS_NOMBRE = {
    "L": "lunes",
    "M": "martes",
    "X": "miercoles",
    "J": "jueves",
    "V": "viernes",
    "S": "sabado",
    "D": "domingo",
}

# Como se acredita el beneficio. La distincion importa para el usuario: el
# descuento se ve en la caja, el reintegro se acredita despues.
REINTEGRO = "reintegro"
DESCUENTO = "descuento"
CUOTAS = "cuotas"


def sin_acentos(texto: str) -> str:
    """Baja a ASCII para poder comparar nombres de comercios entre fuentes."""
    if not texto:
        return ""
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c))


def clave(texto: str) -> str:
    """Normaliza un nombre de comercio a una clave comparable.

    "Supermercados La Gallega " y "la gallega" caen en la misma clave.
    """
    base = sin_acentos(texto or "").lower()
    base = re.sub(r"\b(supermercado|supermercados|super|hipermercado|mercado)\b", " ", base)
    base = re.sub(r"[^a-z0-9]+", " ", base)
    return " ".join(base.split())


def parse_dias(crudo: str | None) -> list[str]:
    """Convierte "VS" en ["V", "S"]. Vacio significa todos los dias."""
    if not crudo:
        return list(DIAS)
    encontrados = [d for d in str(crudo).upper() if d in DIAS]
    # Si no se entiende el codigo, es mas seguro mostrarla todos los dias que
    # esconderla: el usuario puede descartarla leyendo el detalle.
    return encontrados or list(DIAS)


def parse_fecha(crudo) -> str | None:
    """Devuelve ISO YYYY-MM-DD a partir de los formatos que usan las fuentes."""
    if not crudo:
        return None
    if isinstance(crudo, (date, datetime)):
        return crudo.date().isoformat() if isinstance(crudo, datetime) else crudo.isoformat()
    texto = str(crudo).strip()
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for patron in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, patron).date().isoformat()
        except ValueError:
            continue
    return None


def entero(valor) -> int | None:
    """Normaliza montos. 0 y vacio significan "no aplica", no "cero pesos"."""
    if valor in (None, "", "0", 0):
        return None
    try:
        limpio = re.sub(r"[^\d]", "", str(valor))
        return int(limpio) if limpio else None
    except (TypeError, ValueError):
        return None


@dataclass
class Promo:
    """Una promocion vigente, ya normalizada y lista para mostrar."""

    comercio: str
    tipo: str = DESCUENTO
    valor: float | None = None            # porcentaje, o cantidad de cuotas
    tope: int | None = None               # None = sin tope, o desconocido
    tope_periodo: str | None = None       # "mes" | "dia" | "compra"
    tope_por: str | None = None           # "banco" | "usuario" | "promo"
    compra_minima: int | None = None
    # Distingue "la fuente dice que no hay tope" de "la fuente no lo publica".
    # Sin esto mostrariamos "sin tope" en promos cuyo tope simplemente no
    # conocemos, que es la clase de error que hace perder plata en la caja.
    limites_conocidos: bool = False
    dias: list[str] = field(default_factory=lambda: list(DIAS))
    desde: str | None = None
    hasta: str | None = None
    bancos: list[str] = field(default_factory=list)
    medios_debito: list[str] = field(default_factory=list)
    medios_credito: list[str] = field(default_factory=list)
    modalidad: list[str] = field(default_factory=list)
    acumulable: bool | None = None
    titulo: str = ""
    fuente: str = ""
    url: str = ""
    comercio_clave: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        self.comercio_clave = self.comercio_clave or clave(self.comercio)
        self.id = self.id or self.huella()

    def huella(self) -> str:
        """Identidad estable de la promo, para deduplicar y detectar cambios.

        No incluye el tope ni la compra minima a proposito: si el banco cambia
        el tope, queremos reconocerla como la misma promo y reportar el cambio,
        no como una promo nueva.
        """
        partes = [
            self.comercio_clave,
            self.tipo,
            str(self.valor),
            "".join(sorted(self.dias)),
            ",".join(sorted(clave(b) for b in self.bancos)),
        ]
        return hashlib.sha1("|".join(partes).encode("utf-8")).hexdigest()[:12]

    def vigente(self, dia: date | None = None) -> bool:
        dia = dia or date.today()
        hoy = dia.isoformat()
        if self.desde and hoy < self.desde:
            return False
        if self.hasta and hoy > self.hasta:
            return False
        return True

    def aplica_hoy(self, dia: date | None = None) -> bool:
        dia = dia or date.today()
        return self.vigente(dia) and DIAS[dia.weekday()] in self.dias

    def ahorro(self, gasto: float) -> float:
        """Ahorro real en pesos para un gasto dado.

        Es el corazon de la app: un 20% con tope de 25.000 deja de rendir a
        partir de los 125.000, y una promo con minimo de 100.000 no sirve para
        una compra de 40.000. El porcentaje nominal solo no alcanza para decidir.
        """
        if self.tipo == CUOTAS or not self.valor:
            return 0.0
        if self.compra_minima and gasto < self.compra_minima:
            return 0.0
        bruto = gasto * (float(self.valor) / 100.0)
        if self.tope:
            return min(bruto, float(self.tope))
        return bruto

    def porcentaje_efectivo(self, gasto: float) -> float:
        """Que porcentaje termina siendo en la practica para ese gasto."""
        if gasto <= 0:
            return 0.0
        return self.ahorro(gasto) / gasto * 100.0

    def gasto_optimo(self) -> int | None:
        """Monto a partir del cual el tope empieza a diluir el beneficio."""
        if not self.tope or not self.valor:
            return None
        return int(self.tope / (float(self.valor) / 100.0))

    def dict(self) -> dict:
        datos = asdict(self)
        datos["dias_nombre"] = [DIAS_NOMBRE[d] for d in self.dias]
        datos["gasto_optimo"] = self.gasto_optimo()
        return datos


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
