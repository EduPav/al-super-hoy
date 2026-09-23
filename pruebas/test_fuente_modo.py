"""Traduccion de una card de MODO al modelo canonico.

Las cards son escritas a mano y minimas: alcanza con los campos que la
traduccion mira. Un volcado crudo de la API no puede entrar al repo (es publico
y esos volcados traen datos que no revisamos), y ademas envejece peor que esto.
"""

import pytest

from ingesta.fuentes import modo
from ingesta.fuentes.modo_traduccion import a_promo
from ingesta.modelo import CUOTAS, DESCUENTO, REINTEGRO


def card(**cambios) -> dict:
    base = {
        "promo_id": "abc",
        "slug": "20-off-en-la-gallega",
        "title": "20% de descuento en La Gallega",
        "where": "La Gallega",
        "days_of_week": "VS",
        "start_date": "2026-09-01",
        "stop_date": "2026-09-30",
        "payment_flow": "instore,online",
        "content": {"row": [{"text": "La Gallega"}, {"text": "20% de descuento"}]},
    }
    base.update(cambios)
    return base


def test_sin_detalle_no_afirmamos_ningun_limite():
    # El listado no publica el tope. Decir "sin tope" aca seria mentir, y es
    # justo el error que hace perder plata en la caja.
    promo = a_promo(card())

    assert promo.limites_conocidos is False
    assert promo.tope is None
    assert promo.compra_minima is None


def test_con_detalle_se_completan_tope_y_compra_minima():
    detalle = {
        "trigger_params": {
            "pct_promo_value": 20,
            "cap_amount_period": 25_000,
            "cap_period": "month",
            "cap_type": "bank",
            "min_amount": 30_000,
            "discount_mode": "cashback",
        }
    }

    promo = a_promo(card(), detalle)

    assert promo.limites_conocidos is True
    assert (promo.tope, promo.tope_periodo, promo.tope_por) == (25_000, "mes", "banco")
    assert promo.compra_minima == 30_000
    assert promo.tipo == REINTEGRO


def test_el_tipo_sale_del_texto_cuando_el_detalle_no_esta():
    assert a_promo(card()).tipo == DESCUENTO
    reintegro = card(content={"row": [{"text": "Coto"}, {"text": "15% de reintegro"}]})
    assert a_promo(reintegro).tipo == REINTEGRO


def test_las_cuotas_se_leen_como_cantidad_y_no_como_porcentaje():
    promo = a_promo(card(), {"trigger_params": {"installments": [3, 6]}})

    assert (promo.tipo, promo.valor) == (CUOTAS, 6.0)


def test_el_valor_se_lee_del_texto_si_el_detalle_no_lo_trae():
    assert a_promo(card()).valor == 20.0


@pytest.mark.parametrize("generico", ["Comercios adheridos", "Consulta los locales adheridos"])
def test_un_where_generico_no_es_un_comercio(generico):
    # MODO usa esos textos cuando la promo no nombra un local; ahi el nombre
    # real solo esta en el titulo.
    promo = a_promo(card(where=generico, content={"row": [{"text": generico}]}))

    assert promo.comercio == "La Gallega"


def test_los_bancos_salen_de_extra_data():
    filas = [{"text": "La Gallega"}, {"text": "20%"}, {}, {}, {}, {
        "text": "Bancos adheridos",
        "extra_data": [{"name_bank": "Banco Santa Fe"}, {"name_bank": "Galicia"}],
    }]

    assert a_promo(card(content={"row": filas})).bancos == ["Banco Santa Fe", "Galicia"]


def test_bancos_adheridos_no_es_un_banco():
    filas = [{"text": "La Gallega"}, {"text": "20%"}, {}, {}, {}, {"text": "Bancos adheridos"}]

    assert a_promo(card(content={"row": filas})).bancos == []


def test_la_modalidad_se_traduce_a_castellano():
    assert a_promo(card()).modalidad == ["presencial", "online"]


def test_la_url_apunta_a_la_promo_concreta():
    assert a_promo(card()).url.endswith("/20-off-en-la-gallega")
    assert a_promo(card(slug=None)).url == modo.BASE


def test_objeto_embebido_lee_el_payload_escapado_de_next():
    html = 'algo <script>{\\"trigger_params\\":{\\"min_amount\\":1000},\\"otro\\":1}</script>'

    assert modo.objeto_embebido(html, "trigger_params") == {"min_amount": 1000}
    assert modo.objeto_embebido(html, "no_esta") is None
