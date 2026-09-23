"""Fusion entre fuentes y calculo de novedades.

La misma promo suele estar en MODO y en la pagina del banco. MODO aporta el
tope y la compra minima; el banco confirma y a veces suma medios de pago. Si la
fusion pierde el tope, la app vuelve a mentir sobre el limite.
"""

import json

from ingesta.main import Fuente, _novedades, fusionar
from ingesta.modelo import Promo


def test_la_fusion_completa_los_huecos_con_la_otra_fuente():
    rica = Promo(comercio="La Gallega", valor=20, dias=["V"], tope=25_000,
                 compra_minima=30_000, limites_conocidos=True, bancos=["Galicia"],
                 fuente="MODO", url="https://modo/1")
    pobre = Promo(comercio="La Gallega", valor=20, dias=["V"], bancos=["Banco Santa Fe"],
                  fuente="Banco Santa Fe", url="https://bsf/1")

    fusionadas = fusionar([Fuente("Banco Santa Fe", [pobre]), Fuente("MODO", [rica])])

    assert len(fusionadas) == 1
    promo = fusionadas[0]
    assert promo["tope"] == 25_000
    assert promo["compra_minima"] == 30_000
    assert promo["bancos"] == ["Banco Santa Fe", "Galicia"]
    assert [f["nombre"] for f in promo["fuentes"]] == ["Banco Santa Fe", "MODO"]


def test_alcanza_con_que_una_fuente_publique_los_limites():
    # Si alguna publica los limites, ya se puede afirmar "sin tope" en vez de
    # tener que decir "no informado".
    con = Promo(comercio="Dia", valor=10, dias=["L"], limites_conocidos=True, fuente="MODO")
    sin = Promo(comercio="Dia", valor=10, dias=["L"], limites_conocidos=False, fuente="BSF")

    assert fusionar([Fuente("BSF", [sin]), Fuente("MODO", [con])])[0]["limites_conocidos"] is True


def test_promos_distintas_no_se_fusionan():
    lunes = Promo(comercio="Dia", valor=10, dias=["L"])
    viernes = Promo(comercio="Dia", valor=10, dias=["V"])

    assert len(fusionar([Fuente("MODO", [lunes, viernes])])) == 2


def test_no_se_repite_la_misma_fuente_dos_veces():
    # Una promo puede venir de dos avisos de la misma fuente con la misma url.
    una = Promo(comercio="Dia", valor=10, dias=["L"], fuente="MODO", url="https://modo/1")
    otra = Promo(comercio="Dia", valor=10, dias=["L"], fuente="MODO", url="https://modo/1")

    assert len(fusionar([Fuente("MODO", [una, otra])])[0]["fuentes"]) == 1


def _guardar_anterior(tmp_path, monkeypatch, promos):
    archivo = tmp_path / "estado-anterior.json"
    archivo.write_text(
        json.dumps({"generado": "2026-09-19T09:00:00+00:00", "promos": promos}),
        encoding="utf-8",
    )
    monkeypatch.setattr("ingesta.main.ANTERIOR", archivo)


def test_novedades_reporta_altas_bajas_y_cambios(tmp_path, monkeypatch):
    anterior = Promo(comercio="Dia", valor=20, dias=["L"], tope=10_000).dict()
    terminada = Promo(comercio="Coto", valor=15, dias=["M"]).dict()
    _guardar_anterior(tmp_path, monkeypatch, [anterior, terminada])

    # Mismo id (la huella ignora el tope), tope distinto.
    ahora = Promo(comercio="Dia", valor=20, dias=["L"], tope=5_000).dict()
    nueva = Promo(comercio="Carrefour", valor=30, dias=["X"]).dict()

    novedades = _novedades([ahora, nueva])

    assert novedades["nuevas"] == [nueva["id"]]
    assert [t["comercio"] for t in novedades["terminadas"]] == ["Coto"]
    assert novedades["cambios"] == [
        {"id": ahora["id"], "comercio": "Dia", "campo": "tope", "antes": 10_000, "ahora": 5_000}
    ]
    assert novedades["comparado_con"] == "2026-09-19T09:00:00+00:00"


def test_sin_corrida_anterior_no_se_inventan_novedades(tmp_path, monkeypatch):
    monkeypatch.setattr("ingesta.main.ANTERIOR", tmp_path / "no-existe.json")
    promo = Promo(comercio="Dia", valor=20, dias=["L"]).dict()

    novedades = _novedades([promo])

    # Todo es nuevo la primera vez, pero nada figura como terminado.
    assert novedades["nuevas"] == [promo["id"]]
    assert novedades["terminadas"] == []
    assert novedades["comparado_con"] is None
