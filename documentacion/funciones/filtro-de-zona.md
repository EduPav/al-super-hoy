<!-- ultima_verificacion: 2026-09-20 -->
# Función: filtro de zona

## Para qué existe
Las fuentes son nacionales o provinciales. La app es para Santa Fe capital. Este
filtro es lo único que hace que una promo de un supermercado de Córdoba no
aparezca en la lista.

## Dónde vive
- Código: `ingesta/zona.py`
- Registro: `datos/comercios-santa-fe.yml` (se edita a mano)
- En el sitio: la pestaña Fuentes muestra "Sin confirmar" y "No reconocidos"

## Entradas
- `Promo.comercio_clave`: el nombre del comercio ya normalizado
- El registro: `comercios` (con `alias` y `confirmado`) y `descartados`

## Salidas
- `incluye(promo)`: `True`/`False`, y de paso **unifica el nombre** del comercio
- `por_confirmar()`: los del registro que nadie verificó todavía
- `informe_desconocidos()`: los que tienen promo vigente y no están en el
  registro

## Cómo funciona
`contiene(patron, texto)` compara por **palabras completas y contiguas**, no por
subcadena. Y la dirección importa: el nombre del registro tiene que estar dentro
del nombre de la promo, no al revés.

- "Carrefour" reconoce a "Carrefour Express" ✅
- "Carrefour Market" **no** se queda con "Super Market" ✅
- "dia" **no** matchea "diarco", "diamante" ni "cordial" ✅
- "vea" **no** matchea "alvear" ✅

Esos cuatro últimos son falsos positivos que ocurrieron de verdad con la
comparación por subcadena suelta. Están fijados en
`pruebas/test_zona.py::test_contiene_rechaza_las_coincidencias_sueltas`.

Cuando encuentra el comercio, reemplaza el nombre de la promo por el del
registro: sin eso la app mostraría "ChangoMas" y "ChangoMás" como dos comercios.

## Casos borde
| Caso | Qué tiene que pasar |
|---|---|
| Comercio que no está en el registro | Queda anotado en "No reconocidos", no se descarta en silencio |
| Comercio en `descartados` | No entra y tampoco ensucia la lista de revisión |
| `confirmado: false` | Entra igual, pero figura en "Sin confirmar" hasta verificarlo |
| Mismo comercio con dos grafías | Se unifica al nombre del registro |

## Lo que no hace
- No deduce la relevancia geográfica de los datos: **no se puede**. MODO no
  publica las sucursales de cada promo. El registro es una declaración humana.
- No sabe si Banco Santa Fe publicó una promo de Rosario o de la capital. Por
  eso varios comercios arrancan con `confirmado: false`.

## Verificación
- Pruebas: `pruebas/test_zona.py`,
  `pruebas/test_estructura.py::test_el_registro_de_comercios_es_valido`
- Comando: `python -m herramientas.verificar`
- Qué mirar además: después de tocar el filtro, `python -m ingesta.main` y
  revisar el mapeo **comercio por comercio**. Que el total baje no significa que
  esté mal, y que suba no significa que esté bien.

## Relacionado
- [ARQUITECTURA.md](../../ARQUITECTURA.md)
- [../flujos-de-trabajo.md](../flujos-de-trabajo.md) — agregar un comercio
