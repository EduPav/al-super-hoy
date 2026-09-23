"""Lectura del listado de Banco Santa Fe, con una sesion falsa.

El HTML del fixture es minimo y escrito a mano: reproduce la forma que el
parser necesita (un `h4` con el titulo y el `p` siguiente con el detalle), no
una copia de la pagina real.
"""

import pytest
import requests

from ingesta.fuentes import ErrorFuente
from ingesta.fuentes import banco_santa_fe as bsf
from ingesta.modelo import CUOTAS, DESCUENTO, REINTEGRO

PAGINA = """
<html><body>
  <div class="banner"><h4>Beneficios del mes</h4><p>Sin porcentaje: no es una promo.</p></div>
  <div><h4>20% de descuento en La Gallega - Modo</h4>
       <p>Todos los Viernes y Sabados. Vigencia del 01/09/2026 al 30/09/2026.</p></div>
  <div><h4>6 cuotas sin interes en Bacim</h4>
       <p>Todos los dias.</p></div>
  <div><h4>10% Adicional Super del Interior</h4>
       <p>Promocion general.</p></div>
</body></html>
"""


class RespuestaFalsa:
    def __init__(self, texto: str):
        self.text = texto
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:
        return None


class SesionFalsa:
    """Devuelve siempre la misma pagina, como hace el sitio pasado el final."""

    def __init__(self, texto: str = PAGINA, error: Exception | None = None):
        self.texto, self.error, self.llamadas = texto, error, 0

    def get(self, url, **nombrados):
        self.llamadas += 1
        if self.error:
            raise self.error
        return RespuestaFalsa(self.texto)


@pytest.mark.parametrize(
    "titulo,esperado",
    [
        ("20% de descuento en Chango Mas - Modo", (DESCUENTO, 20.0, "Chango Mas", ["Modo"])),
        ("15% de reintegro en La Gallega", (REINTEGRO, 15.0, "La Gallega", [])),
        ("6 cuotas sin interes en Bacim", (CUOTAS, 6.0, "Bacim", [])),
    ],
)
def test_parsear_titulo(titulo, esperado):
    assert bsf._parsear_titulo(titulo) == esperado


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("Todos los Viernes y Sabados", ["V", "S"]),
        ("Todos los dias", ["L", "M", "X", "J", "V", "S", "D"]),
        ("Los miercoles", ["X"]),
        ("Sin dias", ["L", "M", "X", "J", "V", "S", "D"]),
    ],
)
def test_dias(texto, esperado):
    assert bsf._dias(texto) == esperado


def test_vigencia_lee_las_dos_fechas():
    assert bsf._vigencia("Del 01/09/2026 al 30/09/2026") == ("2026-09-01", "2026-09-30")
    assert bsf._vigencia("Desde el 01/09/2026") == ("2026-09-01", None)
    assert bsf._vigencia("Sin fechas") == (None, None)


def test_listar_arma_las_promos_y_deja_afuera_los_banners():
    # "10% Adicional Super del Interior" no nombra un comercio: el nombre
    # quedaria con un porcentaje adentro, y eso no es un comercio.
    promos = bsf.listar(SesionFalsa())

    assert [p.comercio for p in promos] == ["La Gallega", "Bacim"]
    gallega = promos[0]
    assert (gallega.tipo, gallega.valor, gallega.dias) == (DESCUENTO, 20.0, ["V", "S"])
    assert (gallega.desde, gallega.hasta) == ("2026-09-01", "2026-09-30")
    assert gallega.bancos == [bsf.NOMBRE]
    assert gallega.limites_conocidos is False   # el listado no publica topes


def test_listar_corta_cuando_la_pagina_se_repite():
    sesion = SesionFalsa()
    bsf.listar(sesion, max_paginas=8)

    # Pasado el final el sitio repite el ultimo lote; sin el corte por titulos
    # nuevos pedirian las ocho paginas siempre.
    assert sesion.llamadas == 2


def test_si_la_fuente_no_responde_levanta_errorfuente():
    # El orquestador degrada esa fuente y sigue con las demas: nunca ve una
    # excepcion de requests.
    with pytest.raises(ErrorFuente):
        bsf.listar(SesionFalsa(error=requests.ConnectionError("sin red")))


def test_si_no_se_reconoce_nada_tambien_es_un_error():
    with pytest.raises(ErrorFuente):
        bsf.listar(SesionFalsa("<html><body><p>nada</p></body></html>"))
