<!-- ultima_verificacion: 2026-09-20 -->
# Función: fusión y novedades

## Para qué existe
La misma promo suele estar en MODO y en la página del banco. Sin fusionar, la
app la mostraría dos veces con datos distintos. Y sin comparar contra la corrida
anterior, el usuario no se entera de que le bajaron el tope.

## Dónde vive
- Código: `ingesta/main.py` (`fusionar`, `_novedades`)
- Estado previo: `datos/estado-anterior.json`
- En el sitio: la pestaña Novedades

## Cómo funciona la fusión
Dos promos son la misma si coinciden comercio, tipo, valor y días. Cuando se
repiten:

- Los campos vacíos de la primera se completan con los de la segunda (`tope`,
  `tope_periodo`, `tope_por`, `compra_minima`, `acumulable`, `desde`, `hasta`).
- Las listas se unen (`bancos`, medios de pago, modalidad).
- `limites_conocidos` es un OR: alcanza con que **una** fuente publique los
  límites para poder afirmar "sin tope" en vez de "no informado".
- Las fuentes se acumulan, sin repetir la misma url.

## Cómo funcionan las novedades
`Promo.huella()` no incluye el tope ni la compra mínima. Si el banco cambia el
tope, es la misma promo con otro tope: la app reporta el cambio en vez de darla
por terminada e inventar una nueva.

Se comparan cuatro campos: `tope`, `compra_minima`, `valor` y `hasta`.

## Casos borde
| Caso | Qué tiene que pasar |
|---|---|
| No existe `estado-anterior.json` | Todo figura como nuevo y nada como terminado |
| La misma promo llega dos veces de la misma fuente | Una sola entrada de fuente, no dos |
| Una fuente trae el tope y la otra no | Gana el que existe, no el último |
| La promo desaparece de la fuente | Va a "terminadas" con su comercio y título |

## Lo que no hace
- No distingue "la promo terminó" de "la fuente no la publicó hoy". Si MODO
  falla, esa fuente queda marcada como caída y las promos igual pueden figurar
  como terminadas: por eso la pestaña Fuentes está al lado de Novedades.
- No guarda historia: solo compara con la corrida inmediatamente anterior.

## Verificación
- Pruebas: `pruebas/test_fusion.py`
- Comando: `python -m herramientas.verificar`

## Relacionado
- [ARQUITECTURA.md](../../ARQUITECTURA.md)
- [fuentes.md](fuentes.md)
