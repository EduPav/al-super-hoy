"""El filtro de zona: el error que ya paso una vez y no puede volver a pasar.

Comparar nombres de comercio por subcadena suelta mezclo comercios distintos en
una corrida real ("dia" dentro de "diarco", "vea" dentro de "alvear"). Estas
pruebas fijan el comportamiento por palabras completas y contiguas.
"""

import pytest

from ingesta.modelo import Promo
from ingesta.zona import Zona, contiene

REGISTRO = """
comercios:
  - nombre: Supermercados La Gallega
    alias: [La Gallega]
  - nombre: Dia
  - nombre: Carrefour
  - nombre: Alvear
    confirmado: false
descartados:
  - Diarco
"""


@pytest.fixture
def zona(tmp_path):
    archivo = tmp_path / "comercios.yml"
    archivo.write_text(REGISTRO, encoding="utf-8")
    return Zona.cargar(archivo)


@pytest.mark.parametrize(
    "patron,texto",
    [
        ("dia", "dia"),
        ("dia", "dia market"),
        ("carrefour", "carrefour express"),
        ("la gallega", "la gallega centro"),
    ],
)
def test_contiene_reconoce_palabras_completas(patron, texto):
    assert contiene(patron, texto)


@pytest.mark.parametrize(
    "patron,texto",
    [
        ("dia", "diarco"),          # el falso positivo original
        ("dia", "diamante"),
        ("vea", "alvear"),
        ("dia", "cordial"),
        # La direccion importa: el nombre del registro va adentro del nombre de
        # la promo, no al reves. Si no, "Carrefour Market" se quedaria con
        # cualquier "Super Market".
        ("carrefour market", "super market"),
        ("", "dia"),
        ("dia", ""),
    ],
)
def test_contiene_rechaza_las_coincidencias_sueltas(patron, texto):
    assert not contiene(patron, texto)


def test_incluye_unifica_el_nombre_del_comercio(zona):
    # La app no puede mostrar "La Gallega" y "Supermercados La Gallega" como si
    # fueran dos comercios distintos.
    promo = Promo(comercio="LA GALLEGA", valor=20)

    assert zona.incluye(promo)
    assert promo.comercio == "Supermercados La Gallega"


def test_incluye_reconoce_por_alias(zona):
    assert zona.incluye(Promo(comercio="la gallega express", valor=10))


def test_un_comercio_que_no_esta_queda_anotado_para_revisar(zona):
    assert not zona.incluye(Promo(comercio="Super Nuevo", valor=10))
    assert zona.informe_desconocidos() == [{"comercio": "Super Nuevo", "promos": 1}]


def test_un_comercio_descartado_no_ensucia_la_lista_de_revision(zona):
    assert not zona.incluye(Promo(comercio="Diarco", valor=10))
    assert zona.informe_desconocidos() == []


def test_filtrar_deja_solo_los_de_la_zona(zona):
    promos = [
        Promo(comercio="Dia", valor=10),
        Promo(comercio="Diarco", valor=10),
        Promo(comercio="Super Nuevo", valor=10),
    ]

    assert [p.comercio for p in zona.filtrar(promos)] == ["Dia"]


def test_por_confirmar_lista_lo_que_falta_verificar(zona):
    assert zona.por_confirmar() == ["Alvear"]
