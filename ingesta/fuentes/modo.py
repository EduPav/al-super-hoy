"""Fuente MODO: la billetera conjunta de los bancos argentinos.

MODO expone un endpoint REST publico y sin autenticacion que agrega las promos
de mas de 80 entidades. Es la columna vertebral de la app y no cuesta tokens.

El listado trae casi todo, pero NO trae la compra minima ni el tope exacto: eso
vive en la pagina de detalle, que Next.js renderiza en el servidor e incluye un
objeto `trigger_params` con los valores numericos. Por eso el flujo es:
listar (barato, 4 llamadas) -> filtrar por zona -> pedir detalle solo de las que
quedaron.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from ..modelo import (
    CUOTAS,
    DESCUENTO,
    REINTEGRO,
    Promo,
    entero,
    parse_dias,
    parse_fecha,
    sin_acentos,
)

BASE = "https://www.modo.com.ar/promos"
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

# Textos que MODO usa en el campo "where" cuando la promo no nombra un comercio
# concreto. No son nombres de comercio y hay que ignorarlos.
COMERCIO_GENERICO = {
    "comercios adheridos",
    "consulta los locales adheridos",
    "consulta la tienda online adherida",
    "consulta los locales y tienda online adheridos",
    "locales adheridos",
    "todo el pais",
    "carnicerias que acepten modo",
}

CABECERAS = {
    "User-Agent": "al-super-hoy/1.0 (uso personal; lector de promociones publicas)",
    "Accept": "application/json, text/html",
}

# Etiquetas legibles para los codigos internos de MODO.
PERIODOS = {"month": "mes", "day": "dia", "week": "semana", "transaction": "compra"}
ALCANCES = {"bank": "banco", "user": "usuario", "promotion": "promo"}
MODALIDADES = {
    "instore": "presencial",
    "online": "online",
    "instore_nfc": "NFC",
}


class ErrorFuente(Exception):
    """La fuente no pudo leerse. El orquestador decide si degrada o aborta."""


def _sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update(CABECERAS)
    return s


def _listar_slot(sesion: requests.Session, slot: str, categoria: int,
                 max_paginas: int) -> list[dict]:
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


def listar(sesion: requests.Session | None = None, categoria: int = CATEGORIA_MERCADOS,
           max_paginas: int = 20) -> list[dict]:
    """Devuelve todas las promos vigentes del rubro, de todos los carruseles."""
    sesion = sesion or _sesion()
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


def _objeto_embebido(texto: str, llave: str) -> dict | None:
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


def detalle(slug: str, sesion: requests.Session | None = None,
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

    sesion = sesion or _sesion()
    try:
        r = sesion.get(f"{BASE}/{slug}", timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        html = r.text
    except requests.RequestException:
        return {}

    datos = {
        "trigger_params": _objeto_embebido(html, "trigger_params") or {},
        "promotion": _objeto_embebido(html, "promotion") or {},
    }
    if cache and datos["trigger_params"]:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{slug}.json").write_text(
            json.dumps(datos, ensure_ascii=False), encoding="utf-8"
        )
    return datos


def _fila(card: dict, indice: int) -> str:
    filas = (card.get("content") or {}).get("row") or []
    if indice < len(filas):
        return (filas[indice] or {}).get("text") or ""
    return ""


def _bancos(card: dict) -> list[str]:
    """Nombres de banco. MODO los pone en extra_data cuando es exclusiva."""
    filas = (card.get("content") or {}).get("row") or []
    if len(filas) < 6:
        return []
    fila = filas[5] or {}
    extra = fila.get("extra_data") or []
    nombres = [e.get("name_bank") for e in extra if isinstance(e, dict) and e.get("name_bank")]
    if nombres:
        return nombres
    texto = (fila.get("text") or "").strip()
    # "Bancos adheridos" no es un banco: significa que aplica a varios.
    if texto and "adherido" not in texto.lower():
        return [texto]
    return []


def _desde_titulo(titulo: str) -> str:
    """Saca el comercio del titulo: "20% de reintegro en MasGo" -> "MasGo"."""
    titulo = (titulo or "").strip()
    encontrado = re.match(r"^\s*\d+(?:[.,]\d+)?\s*%.*?\ben\s+(.+)$", titulo, re.IGNORECASE)
    return (encontrado.group(1) if encontrado else titulo).strip()


def _nombre_comercio(card: dict) -> str:
    """Resuelve el nombre del comercio entre los tres lugares donde puede estar.

    MODO a veces pone en `where` un texto generico ("Consulta los locales
    adheridos"), y ahi el nombre real solo aparece en el titulo de la promo.
    """
    for candidato in ((card.get("where") or ""), _fila(card, 0)):
        candidato = candidato.strip()
        if candidato and sin_acentos(candidato).lower() not in COMERCIO_GENERICO:
            return candidato
    return _desde_titulo(card.get("title") or "")


def _tipo_y_valor(card: dict, params: dict) -> tuple[str, float | None]:
    """Determina si es reintegro, descuento o cuotas, y su valor numerico."""
    cuotas = params.get("installments") or []
    if cuotas and not params.get("pct_promo_value"):
        try:
            return CUOTAS, float(max(int(c) for c in cuotas))
        except (TypeError, ValueError):
            return CUOTAS, None

    modo_descuento = (params.get("discount_mode") or "").lower()
    texto = _fila(card, 1).lower()
    if "cashback" in modo_descuento or "reintegro" in texto:
        tipo = REINTEGRO
    elif "descuento" in texto or modo_descuento:
        tipo = DESCUENTO
    else:
        tipo = REINTEGRO if "reintegro" in (card.get("title") or "").lower() else DESCUENTO

    valor = (
        params.get("pct_promo_value")
        or params.get("debit_promo_value")
        or params.get("credit_promo_value")
    )
    if not valor:
        encontrado = re.search(r"(\d+(?:[.,]\d+)?)\s*%", texto or card.get("title") or "")
        valor = float(encontrado.group(1).replace(",", ".")) if encontrado else None
    return tipo, float(valor) if valor else None


def a_promo(card: dict, det: dict | None = None) -> Promo:
    """Traduce una card de MODO (mas su detalle opcional) al modelo canonico."""
    det = det or {}
    params = det.get("trigger_params") or {}

    comercio = _nombre_comercio(card)

    tipo, valor = _tipo_y_valor(card, params)

    # El tope preciso esta en el detalle; el listado solo trae el texto de la card.
    tope = entero(params.get("cap_amount_period")) or entero(_fila(card, 4))
    modalidad = [
        MODALIDADES.get(m.strip(), m.strip())
        for m in (card.get("payment_flow") or "").split(",")
        if m.strip()
    ]

    return Promo(
        comercio=comercio,
        tipo=tipo,
        valor=valor,
        tope=tope,
        tope_periodo=PERIODOS.get(params.get("cap_period") or "", None),
        tope_por=ALCANCES.get(params.get("cap_type") or "", None),
        compra_minima=entero(params.get("min_amount")),
        # Solo el detalle publica los limites. Sin el, no afirmamos nada.
        limites_conocidos=bool(params),
        dias=parse_dias(card.get("days_of_week")),
        desde=parse_fecha(card.get("start_date")),
        hasta=parse_fecha(card.get("stop_date")),
        bancos=_bancos(card),
        medios_debito=list(card.get("debit_list") or params.get("debit_list") or []),
        medios_credito=list(card.get("credit_list") or params.get("credit_list") or []),
        modalidad=modalidad,
        acumulable=(card.get("exclusiveness") == "all") or None,
        titulo=(card.get("title") or "").strip(),
        fuente="MODO",
        url=f"{BASE}/{card.get('slug')}" if card.get("slug") else BASE,
    )
