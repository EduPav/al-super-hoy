"""Traduccion de una card de MODO al modelo canonico. Sin red, sin estado.

Vive separado de `modo.py` a proposito: aca no se abre un socket, asi que todo
este modulo se prueba con una card escrita a mano y sin tocar la API. Es la
mitad del codigo donde se decide que ve el usuario (tipo, valor, tope, comercio)
y por eso es la mitad que tiene que estar cubierta por pruebas.
"""

from __future__ import annotations

import re

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

# `NOMBRE` y `BASE` identifican a la fuente. Viven en el modulo hoja para que
# `modo.py` los importe desde aca y no haya dos copias del nombre: uno solo es
# el que ve el usuario en la pestana Fuentes y el que se guarda en cada promo.
NOMBRE = "MODO"
BASE = "https://www.modo.com.ar/promos"

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

# Etiquetas legibles para los codigos internos de MODO.
PERIODOS = {"month": "mes", "day": "dia", "week": "semana", "transaction": "compra"}
ALCANCES = {"bank": "banco", "user": "usuario", "promotion": "promo"}
MODALIDADES = {
    "instore": "presencial",
    "online": "online",
    "instore_nfc": "NFC",
}


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
        fuente=NOMBRE,
        url=f"{BASE}/{card.get('slug')}" if card.get("slug") else BASE,
    )
