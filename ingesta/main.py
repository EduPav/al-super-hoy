"""Orquestador de la ingesta diaria.

Flujo:
  1. Lee cada fuente de forma independiente.
  2. Filtra por el registro de comercios de Santa Fe capital.
  3. Pide el detalle solo de las promos que sobrevivieron al filtro, que es
     donde estan el tope y la compra minima.
  4. Fusiona las promos repetidas entre fuentes.
  5. Compara contra la corrida anterior y escribe el resultado.

Principio de diseno: si una fuente falla, el resto sigue. Nunca se borra lo que
ya se sabia; se marca como desactualizado y la app lo muestra. Es preferible
avisar que el dato tiene tres dias a mostrarlo como si fuera de hoy.

Uso:  python -m ingesta.main
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from .fuentes import banco_santa_fe, modo
from .modelo import Promo, ahora_iso, clave
from .zona import Zona

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "datos"
CACHE = RAIZ / "datos" / "cache"
ANTERIOR = RAIZ / "datos" / "estado-anterior.json"


@dataclass
class Fuente:
    """Resultado de leer una fuente, con su estado para el panel de salud."""

    nombre: str
    promos: list[Promo] = field(default_factory=list)
    ok: bool = True
    error: str = ""


def _leer_modo(zona: Zona, sesion: requests.Session) -> Fuente:
    try:
        cards = modo.listar(sesion)
    except modo.ErrorFuente as exc:
        return Fuente("MODO", ok=False, error=str(exc))

    # Primero filtramos con lo que ya trae el listado y despues pedimos el
    # detalle. Asi bajamos de ~380 paginas de detalle a un par de docenas.
    promos = []
    for card in cards:
        preliminar = modo.a_promo(card)
        if not zona.incluye(preliminar):
            continue
        slug = card.get("slug")
        completa = modo.a_promo(card, modo.detalle(slug, sesion, cache=CACHE) if slug else {})
        # zona.incluye ya unifico el nombre del comercio; lo conservamos.
        completa.comercio = preliminar.comercio
        completa.comercio_clave = preliminar.comercio_clave
        promos.append(completa)
    return Fuente("MODO", promos=promos)


def _leer_banco_santa_fe(zona: Zona, sesion: requests.Session) -> Fuente:
    try:
        promos = banco_santa_fe.listar(sesion)
    except banco_santa_fe.ErrorFuente as exc:
        return Fuente("Banco Santa Fe", ok=False, error=str(exc))
    return Fuente("Banco Santa Fe", promos=zona.filtrar(promos))


def _llave_fusion(p: Promo) -> tuple:
    """Dos promos son la misma si coinciden comercio, tipo, valor y dias."""
    return (p.comercio_clave, p.tipo, p.valor, "".join(sorted(p.dias)))


def fusionar(fuentes: list[Fuente]) -> list[dict]:
    """Unifica promos repetidas entre fuentes, quedandose con el dato mas rico.

    La misma promo suele estar en MODO y en la pagina del banco. MODO aporta el
    tope y la compra minima; el banco confirma y a veces agrega el suyo.
    """
    fusionadas: dict[tuple, dict] = {}
    for fuente in fuentes:
        for p in fuente.promos:
            llave = _llave_fusion(p)
            registro = p.dict()
            registro["fuentes"] = [{"nombre": fuente.nombre, "url": p.url}]

            previa = fusionadas.get(llave)
            if not previa:
                fusionadas[llave] = registro
                continue

            # Completamos los huecos de la que ya teniamos.
            for campo in ("tope", "tope_periodo", "tope_por", "compra_minima",
                          "acumulable", "desde", "hasta"):
                if previa.get(campo) in (None, "") and registro.get(campo) not in (None, ""):
                    previa[campo] = registro[campo]
            for campo in ("bancos", "medios_debito", "medios_credito", "modalidad"):
                previa[campo] = sorted({*previa.get(campo, []), *registro.get(campo, [])})
            # Alcanza con que una fuente publique los limites para poder
            # afirmar "sin tope" en vez de "no informado".
            previa["limites_conocidos"] = (
                previa.get("limites_conocidos") or registro.get("limites_conocidos")
            )
            urls = {f["url"] for f in previa["fuentes"]}
            previa["fuentes"] += [f for f in registro["fuentes"] if f["url"] not in urls]

    return list(fusionadas.values())


def _novedades(promos: list[dict]) -> dict:
    """Compara contra la corrida anterior: que entro, que salio, que cambio."""
    try:
        previo = json.loads(ANTERIOR.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previo = {}

    antes = {p["id"]: p for p in previo.get("promos", [])}
    ahora = {p["id"]: p for p in promos}

    cambios = []
    for pid, p in ahora.items():
        vieja = antes.get(pid)
        if not vieja:
            continue
        for campo, etiqueta in (("tope", "tope"), ("compra_minima", "compra minima"),
                                ("valor", "porcentaje"), ("hasta", "vigencia")):
            if vieja.get(campo) != p.get(campo):
                cambios.append({
                    "id": pid,
                    "comercio": p["comercio"],
                    "campo": etiqueta,
                    "antes": vieja.get(campo),
                    "ahora": p.get(campo),
                })

    return {
        "nuevas": [p["id"] for p in promos if p["id"] not in antes],
        "terminadas": [
            {"id": pid, "comercio": p["comercio"], "titulo": p.get("titulo", "")}
            for pid, p in antes.items() if pid not in ahora
        ],
        "cambios": cambios,
        "comparado_con": previo.get("generado"),
    }


def main() -> int:
    zona = Zona.cargar()
    sesion = requests.Session()

    fuentes = [_leer_modo(zona, sesion), _leer_banco_santa_fe(zona, sesion)]
    promos = fusionar(fuentes)

    hoy = date.today()
    for p in promos:
        p["aplica_hoy"] = (
            (not p.get("desde") or p["desde"] <= hoy.isoformat())
            and (not p.get("hasta") or p["hasta"] >= hoy.isoformat())
            and ["L", "M", "X", "J", "V", "S", "D"][hoy.weekday()] in p["dias"]
        )
    promos.sort(key=lambda p: (-(p.get("valor") or 0), p["comercio"]))

    salida = {
        "generado": ahora_iso(),
        "zona": "Santa Fe capital",
        "promos": promos,
        "comercios": sorted({p["comercio"] for p in promos}),
        "bancos": sorted({b for p in promos for b in p.get("bancos", [])}),
        "fuentes": [
            {"nombre": f.nombre, "ok": f.ok, "error": f.error, "promos": len(f.promos)}
            for f in fuentes
        ],
        "revisar": {
            "por_confirmar": zona.por_confirmar(),
            "desconocidos": zona.informe_desconocidos(),
        },
    }
    salida["novedades"] = _novedades(promos)

    if not promos and not any(f.ok for f in fuentes):
        # Todas las fuentes cayeron: preservamos el archivo anterior para que la
        # app siga mostrando algo, con el aviso de que esta desactualizado.
        print("ERROR: ninguna fuente respondio. Se conserva el dato anterior.")
        return 1

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "promos.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    ANTERIOR.parent.mkdir(parents=True, exist_ok=True)
    ANTERIOR.write_text(
        json.dumps({"generado": salida["generado"], "promos": promos}, ensure_ascii=False),
        encoding="utf-8",
    )

    for f in fuentes:
        estado = f"{len(f.promos)} promos" if f.ok else f"FALLO: {f.error[:80]}"
        print(f"  {f.nombre:18s} {estado}")
    print(f"  {'TOTAL':18s} {len(promos)} promos en {len(salida['comercios'])} comercios")
    nuevas = len(salida["novedades"]["nuevas"])
    if nuevas:
        print(f"  {'novedades':18s} {nuevas} nuevas, "
              f"{len(salida['novedades']['terminadas'])} terminadas, "
              f"{len(salida['novedades']['cambios'])} cambios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
