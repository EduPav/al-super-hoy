<!-- ultima_verificacion: 2026-09-20 -->
# Función: fuentes

## Para qué existe
Las promos las publican los bancos y los comercios, cada uno a su manera. Esta
capa las trae y las traduce a un solo modelo, para que el resto del sistema no
sepa de dónde salió cada una.

## Dónde vive
- Contrato y sesión HTTP: `ingesta/fuentes/__init__.py`
- MODO: `ingesta/fuentes/modo.py` (red) y `modo_traduccion.py` (traducción)
- Banco Santa Fe: `ingesta/fuentes/banco_santa_fe.py`
- Ejemplo a seguir para una fuente nueva: `modo.py` + `modo_traduccion.py`

## Qué aporta cada una

| Fuente | Qué aporta | Cómo se lee |
|---|---|---|
| **MODO** | El grueso. Agrega las promos de +80 bancos, con tope exacto, compra mínima, días, medios de pago y vigencia | API REST pública, sin autenticación |
| **Banco Santa Fe** | Las promos locales que MODO no lista (La Gallega, Bacim, Alfa, Beltrán, El Túnel, Kilbel, Alvear) | HTML renderizado en el servidor, parseado con reglas fijas |

Ninguna de las dos es una API contratada ni documentada: son endpoints públicos
que pueden cambiar sin aviso. Por eso la app muestra siempre cuándo se actualizó
por última vez y cuál fuente falló.

## El contrato
Cada módulo con `listar` es una fuente y tiene que declarar `NOMBRE`, exponer
`listar(sesion=None)` y levantar el `ErrorFuente` compartido ante cualquier
fallo. Lo verifica
`pruebas/test_estructura.py::test_cada_fuente_cumple_el_contrato`.

## Cómo funciona MODO
- Las promos están repartidas en tres carruseles (`SLOTS`) y ninguno las tiene
  todas: las cadenas grandes viven en "supermercados" y los comercios de barrio
  en "mas-promos". Se leen los tres y se deduplica por `promo_id`.
- El listado **no** trae el tope ni la compra mínima: eso está en la página de
  detalle, dentro del payload que Next.js serializa en el HTML
  (`trigger_params`).
- El detalle se pide solo de las promos que pasaron el filtro de zona, y se
  cachea 20 horas en `datos/cache/`.

## Cómo funciona Banco Santa Fe
- La página se renderiza en el servidor: un `h4` con el título y el `p`
  siguiente con el detalle.
- La paginación es por `skip` en pasos de 12. Pasado el final la página repite
  el último lote en vez de devolver vacío, así que se corta cuando no aparecen
  títulos nuevos.
- Los banners del listado ("10% Adicional Super del Interior") no nombran un
  comercio: se reconocen porque el nombre quedaría con un `%` adentro.

## Casos borde
| Caso | Qué tiene que pasar |
|---|---|
| Una fuente no responde | `ErrorFuente`; el orquestador la marca caída y sigue con las demás |
| Una fuente responde pero no se reconoce nada | También `ErrorFuente`: un 200 vacío es un fallo, no "hoy no hay promos" |
| Un slot de MODO falla y los otros andan | Se usan los que andan; el fallo queda en el mensaje |
| La página de detalle no se puede leer | Se devuelve `{}` y se conserva lo que el listado sabía, con `limites_conocidos` en `False` |
| El campo `where` es genérico ("Consulta los locales adheridos") | El nombre real se saca del título |

## Lo que no hace
- No decide qué se publica: eso es el [filtro de zona](filtro-de-zona.md).
- No afirma un límite que la fuente no publicó. Sin detalle,
  `limites_conocidos` queda en `False` y la app dice "Ahorrás hasta $X".

## Verificación
- Pruebas: `pruebas/test_fuente_modo.py`,
  `pruebas/test_fuente_banco_santa_fe.py`
- Comando: `python -m herramientas.verificar`
- Qué mirar además: ninguna prueba ve que la fuente cambió su HTML esta mañana.
  Después de tocar una fuente, `python -m ingesta.main` y mirar los totales por
  fuente.

## Relacionado
- [ARQUITECTURA.md](../../ARQUITECTURA.md)
- [../seguridad.md](../seguridad.md) — el trato con las fuentes
