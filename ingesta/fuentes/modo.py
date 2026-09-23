"""Fuente MODO: la billetera conjunta de los bancos argentinos.

MODO expone un endpoint REST publico y sin autenticacion que agrega las promos
de mas de 80 entidades. Es la columna vertebral de la app y no cuesta tokens.

El listado trae casi todo, pero NO trae la compra minima ni el tope exacto: eso
vive en la pagina de detalle, que Next.js renderiza en el servidor e incluye un
objeto `trigger_params` con los valores numericos. Por eso el flujo es:
listar (barato, 3 slots) -> filtrar por zona -> pedir detalle solo de las que
quedaron.

Este modulo es la mitad con red. La traduccion de una card al modelo canonico
vive en `modo_traduccion.py`, que no abre sockets y se prueba sola.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from . import ErrorFuente, Sesion
from . import sesion as abrir_sesion
from .modo_traduccion import BASE, NOMBRE, a_promo

__all__ = ["BASE", "NOMBRE", "ErrorFuente", "a_promo", "detalle", "listar", "objeto_embebido"]

API = f"{BASE}/api/rewards"

# Categoria 1 = "Mercados" (supermercados, autoservicios, kioscos, almacenes).
CATEGORIA_MERCADOS = 1

# MODO reparte las promos en carruseles distintos y no hay uno que las tenga
# todas: las grandes cadenas viven en "supermercados" y los comercios de barrio
# en "mas-promos". Hay que leer los tres y deduplicar por promo_id.
SLOTS = (
    "web-modo-hub-supermercados",
    "web-modo-hub-mas-promos",
    "web-modo-hub-destacadas",
)


def _listar_slot(sesion: Sesion, slot: str, categoria: int, max_paginas: int) -> list[dict]:
    cards: list[dict] = []
    for pagina in range(1, max_paginas + 1):
        parametros = {
            "slots": slot,
            "limit": 50,
            "page": pagina,
            "source": "web_modo",
            "origin": "web_modo",
            "fcalcstatus": "running",
            "slot_info": "true",
            "categories": categoria,
        }
        try:
            r = sesion.get(f"{API}/slots", params=parametros, timeout=30)
            r.raise_for_status()
            lote = r.json().get("data", {}).get("cards", []) or []
        except (requests.RequestException, ValueError) as exc:
            if cards:
                # Ya tenemos parte del catalogo: preferimos datos parciales a nada.
                break
            raise ErrorFuente(f"MODO: slot {slot} fallo en pagina {pagina}: {exc}") from exc
        if not lote:
            break
        cards.extend(lote)
    return cards


def listar(sesion: Sesion | None = None, categoria: int = CATEGORIA_MERCADOS,
           max_paginas: int = 20) -> list[dict]:
    """Devuelve todas las promos vigentes del rubro, de todos los carruseles."""
    sesion = sesion or abrir_sesion()
    vistas: dict[str, dict] = {}
    fallos: list[str] = []
    for slot in SLOTS:
        try:
            for card in _listar_slot(sesion, slot, categoria, max_paginas):
                # promo_id identifica la promo; id identifica la tarjeta que la
                # muestra, y la misma promo aparece en varios carruseles.
                llave = card.get("promo_id") or card.get("id")
                if llave and llave not in vistas:
                    vistas[llave] = card
        except ErrorFuente as exc:
            fallos.append(str(exc))
    if not vistas:
        raise ErrorFuente("MODO no devolvio ninguna promo. " + " / ".join(fallos))
    return list(vistas.values())


def objeto_embebido(texto: str, llave: str) -> dict | None:
    """Extrae un objeto JSON del payload que Next.js serializa en el HTML.

    El payload viene con las comillas escapadas dentro de strings JS, asi que
    primero desescapamos y despues balanceamos llaves desde la clave buscada.
    """
    plano = texto.replace('\\"', '"')
    marca = f'"{llave}":{{'
    inicio = plano.find(marca)
    if inicio == -1:
        return None
    inicio += len(marca) - 1
    profundidad = 0
    for i in range(inicio, len(plano)):
        if plano[i] == "{":
            profundidad += 1
        elif plano[i] == "}":
            profundidad -= 1
            if profundidad == 0:
                try:
                    return json.loads(plano[inicio:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def detalle(slug: str, sesion: Sesion | None = None,
            cache: Path | None = None, max_edad_horas: int = 20) -> dict:
    """Trae tope exacto y compra minima desde la pagina de detalle.

    Devuelve {} si la pagina no se puede leer: el orquestador se queda con lo
    que sabia por el listado en vez de perder la promo entera.
    """
    if cache:
        archivo = cache / f"{slug}.json"
        if archivo.exists() and (time.time() - archivo.stat().st_mtime) < max_edad_horas * 3600:
            try:
                return json.loads(archivo.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

    sesion = sesion or abrir_sesion()
    try:
        r = sesion.get(f"{BASE}/{slug}", timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        html = r.text
    except requests.RequestException:
        return {}

    datos = {
        "trigger_params": objeto_embebido(html, "trigger_params") or {},
        "promotion": objeto_embebido(html, "promotion") or {},
    }
    if cache and datos["trigger_params"]:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{slug}.json").write_text(
            json.dumps(datos, ensure_ascii=False), encoding="utf-8"
        )
    return datos
