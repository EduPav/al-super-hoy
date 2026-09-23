"""El calculo de ahorro es lo unico que la app promete. Tiene que estar bien.

Cada caso de aca sale de una forma concreta de perder plata en la caja: creer
que un 20% rinde 20% pasado el tope, o que una promo con minimo sirve para una
compra chica.
"""

from datetime import date

import pytest

from ingesta.modelo import (
    CUOTAS,
    DESCUENTO,
    Promo,
    clave,
    entero,
    parse_dias,
    parse_fecha,
    sin_acentos,
)


def test_clave_ignora_el_rubro_y_los_acentos():
    assert clave("Supermercados La Gallega ") == clave("la gallega")
    assert clave("ChangoMás") == clave("ChangoMas")


def test_sin_acentos_deja_el_texto_comparable():
    assert sin_acentos("miércoles") == "miercoles"


@pytest.mark.parametrize(
    "crudo,esperado",
    [
        ("VS", ["V", "S"]),
        ("", ["L", "M", "X", "J", "V", "S", "D"]),
        (None, ["L", "M", "X", "J", "V", "S", "D"]),
        # Un codigo que no se entiende se muestra todos los dias: esconder la
        # promo es peor que mostrarla de mas, porque el usuario puede descartarla.
        ("???", ["L", "M", "X", "J", "V", "S", "D"]),
    ],
)
def test_parse_dias(crudo, esperado):
    assert parse_dias(crudo) == esperado


@pytest.mark.parametrize(
    "crudo,esperado",
    [
        ("2026-09-20", "2026-09-20"),
        ("20/09/2026", "2026-09-20"),
        ("2026-09-20T03:00:00Z", "2026-09-20"),
        ("el viernes", None),
        (None, None),
    ],
)
def test_parse_fecha(crudo, esperado):
    assert parse_fecha(crudo) == esperado


@pytest.mark.parametrize(
    "crudo,esperado",
    [
        ("$25.000", 25000), ("25000", 25000), ("0", None),
        ("", None), (None, None), ("sin tope", None),
    ],
)
def test_entero_trata_el_cero_como_no_aplica(crudo, esperado):
    # 0 no es "cero pesos de tope": es "la fuente no publico un tope".
    assert entero(crudo) == esperado


def test_el_tope_derrumba_el_porcentaje_efectivo():
    promo = Promo(comercio="La Gallega", valor=20, tope=25_000, limites_conocidos=True)

    assert promo.ahorro(100_000) == 20_000        # todavia rinde el 20%
    assert promo.ahorro(200_000) == 25_000        # el tope corta
    assert promo.gasto_optimo() == 125_000        # a partir de aca se diluye
    assert promo.porcentaje_efectivo(250_000) == pytest.approx(10.0)


def test_la_compra_minima_anula_la_promo_por_debajo():
    promo = Promo(comercio="Alvear", valor=30, compra_minima=100_000, limites_conocidos=True)

    assert promo.ahorro(40_000) == 0
    assert promo.ahorro(100_000) == 30_000


def test_sin_tope_el_ahorro_no_se_corta():
    promo = Promo(comercio="Carrefour", valor=10, tope=None, limites_conocidos=True)

    assert promo.ahorro(500_000) == 50_000
    assert promo.gasto_optimo() is None


def test_las_cuotas_no_son_ahorro_en_pesos():
    promo = Promo(comercio="Coto", tipo=CUOTAS, valor=6)

    assert promo.ahorro(100_000) == 0


def test_la_huella_ignora_el_tope_para_reconocer_la_misma_promo():
    # Si el banco baja el tope, es la misma promo con otro tope: la app tiene
    # que reportar el cambio, no inventar una promo nueva y dar la vieja por
    # terminada.
    antes = Promo(comercio="La Gallega", valor=20, tope=25_000, dias=["V"])
    despues = Promo(comercio="La Gallega", valor=20, tope=15_000, dias=["V"])

    assert antes.id == despues.id


def test_la_huella_distingue_promos_distintas():
    gallega = Promo(comercio="La Gallega", valor=20, dias=["V"])
    coto = Promo(comercio="Coto", valor=20, dias=["V"])

    assert gallega.id != coto.id


def test_aplica_hoy_mira_dia_y_vigencia():
    viernes = date(2026, 9, 18)
    promo = Promo(comercio="Dia", valor=15, dias=["V"], desde="2026-09-01", hasta="2026-09-30")

    assert promo.aplica_hoy(viernes)
    assert not promo.aplica_hoy(date(2026, 9, 19))          # sabado
    assert not promo.aplica_hoy(date(2026, 10, 2))          # vencida
    assert not promo.vigente(date(2026, 8, 30))             # todavia no empezo


def test_dict_agrega_lo_que_la_web_necesita():
    datos = Promo(comercio="Dia", tipo=DESCUENTO, valor=20, tope=10_000, dias=["L"]).dict()

    assert datos["dias_nombre"] == ["lunes"]
    assert datos["gasto_optimo"] == 50_000
    assert datos["limites_conocidos"] is False
