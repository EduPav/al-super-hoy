"""Fuente Banco Santa Fe: el banco con mas peso en la ciudad.

Aporta promos que MODO no lista, sobre todo de cadenas locales (La Gallega,
Bacim, Alfa, Beltran). La pagina se renderiza en el servidor, asi que se parsea
con reglas fijas y sin LLM.

Limite conocido: el listado no publica el tope ni la compra minima (viven en un
dialogo que se carga aparte). Cuando la promo tambien esta en MODO, la fusion se
queda con los numeros de MODO; cuando no, se muestra sin tope y con el link a la
fuente para que el usuario lo verifique.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from ..modelo import CUOTAS, DESCUENTO, DIAS, REINTEGRO, Promo, parse_fecha, sin_acentos
from . import ErrorFuente, Sesion
from . import sesion as abrir_sesion

NOMBRE = "Banco Santa Fe"
URL = "https://www.bancosantafe.com.ar/beneficios-supermercados"

__all__ = ["NOMBRE", "URL", "ErrorFuente", "listar"]

NOMBRE_A_LETRA = {
    "lunes": "L",
    "martes": "M",
    "miercoles": "X",
    "jueves": "J",
    "viernes": "V",
    "sabados": "S",
    "sabado": "S",
    "domingos": "D",
    "domingo": "D",
}


def _dias(texto: str) -> list[str]:
    """Extrae los dias de frases como "Todos los Viernes y Sabados"."""
    plano = sin_acentos(texto).lower()
    if "todos los dias" in plano:
        return list(DIAS)
    encontrados = []
    for nombre, letra in NOMBRE_A_LETRA.items():
        if re.search(rf"\b{nombre}\b", plano) and letra not in encontrados:
            encontrados.append(letra)
    return sorted(encontrados, key=DIAS.index) if encontrados else list(DIAS)


def _vigencia(texto: str) -> tuple[str | None, str | None]:
    fechas = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
    desde = parse_fecha(fechas[0]) if fechas else None
    hasta = parse_fecha(fechas[1]) if len(fechas) > 1 else None
    return desde, hasta


def _parsear_titulo(titulo: str) -> tuple[str, float | None, str, list[str]]:
    """"20% de descuento en Chango Mas - Modo" -> tipo, valor, comercio, medios."""
    limpio = " ".join(titulo.split())

    medios: list[str] = []
    # El sufijo " - Modo" indica el medio de pago, no forma parte del nombre.
    partes = re.split(r"\s+-\s+", limpio)
    if len(partes) > 1 and len(partes[-1]) <= 20:
        medios.append(partes[-1].strip())
        limpio = " - ".join(partes[:-1])

    cuotas = re.match(r"^\s*(\d+)\s+cuotas?\s+sin\s+inter", sin_acentos(limpio), re.IGNORECASE)
    if cuotas:
        tipo, valor = CUOTAS, float(cuotas.group(1))
    else:
        porcentaje = re.search(r"(\d+(?:[.,]\d+)?)\s*%", limpio)
        valor = float(porcentaje.group(1).replace(",", ".")) if porcentaje else None
        plano = sin_acentos(limpio).lower()
        tipo = REINTEGRO if "reintegro" in plano else DESCUENTO

    comercio = re.sub(r"^.*?\ben\s+", "", limpio, flags=re.IGNORECASE).strip()
    return tipo, valor, comercio or limpio, medios


def _pagina(sesion: Sesion, skip: int) -> list[tuple[str, str]]:
    """Devuelve los pares (titulo, detalle) de una pagina del listado."""
    try:
        r = sesion.get(URL, params={"skip": skip} if skip else None, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.RequestException as exc:
        raise ErrorFuente(f"Banco Santa Fe no respondio (skip={skip}): {exc}") from exc

    sopa = BeautifulSoup(r.text, "html.parser")
    filas = []
    for encabezado in sopa.find_all("h4"):
        titulo = encabezado.get_text(" ", strip=True)
        if not titulo or not re.search(r"\d", titulo):
            continue
        detalle = encabezado.find_next("p")
        filas.append((titulo, detalle.get_text(" ", strip=True) if detalle else ""))
    return filas


def listar(sesion: Sesion | None = None, max_paginas: int = 8) -> list[Promo]:
    """Recorre el listado completo.

    La paginacion es por `skip` en pasos de 12. Pasado el final la pagina repite
    el ultimo lote en vez de devolver vacio, asi que cortamos cuando no aparecen
    titulos nuevos.
    """
    sesion = sesion or abrir_sesion()
    promos: list[Promo] = []
    vistos: set[str] = set()
    fallo_inicial: ErrorFuente | None = None

    for pagina in range(max_paginas):
        try:
            filas = _pagina(sesion, pagina * 12)
        except ErrorFuente as exc:
            if pagina == 0:
                fallo_inicial = exc
            break

        nuevos = 0
        for titulo, texto in filas:
            if titulo in vistos:
                continue
            vistos.add(titulo)
            nuevos += 1

            tipo, valor, comercio, medios = _parsear_titulo(titulo)
            # Los banners del listado ("10% Adicional Super del Interior") no
            # nombran un comercio: quedan con un porcentaje dentro del nombre.
            if not comercio or "%" in comercio:
                continue
            desde, hasta = _vigencia(texto)
            promos.append(
                Promo(
                    comercio=comercio,
                    tipo=tipo,
                    valor=valor,
                    dias=_dias(texto),
                    desde=desde,
                    hasta=hasta,
                    bancos=[NOMBRE],
                    modalidad=medios,
                    titulo=titulo,
                    fuente=NOMBRE,
                    url=URL,
                )
            )
        if not nuevos:
            break

    if fallo_inicial:
        raise fallo_inicial
    if not promos:
        raise ErrorFuente("Banco Santa Fe respondio pero no se reconocio ninguna promo")
    return promos
