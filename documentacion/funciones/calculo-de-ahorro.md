<!-- ultima_verificacion: 2026-09-20 -->
# Función: cálculo de ahorro

## Para qué existe
Una lista de porcentajes no sirve para decidir dónde comprar. Un 20% con tope de
$25.000 rinde 20% solo hasta los $125.000; de ahí en más el porcentaje efectivo
se derrumba. Y una promo con mínimo de $100.000 no sirve para una compra de
$40.000. Esta función convierte el porcentaje anunciado en pesos reales.

## Dónde vive
- Código: `ingesta/modelo.py` (`Promo.ahorro`, `porcentaje_efectivo`,
  `gasto_optimo`)
- Copia en el navegador: `docs/app.js` (`ahorro`, `porcentajeEfectivo`)
- En el sitio: la barra "¿Cuánto vas a gastar?" y el orden de la lista

## Entradas
- `gasto`: float (lo que el usuario escribe en la barra)
- La promo ya normalizada: `valor`, `tipo`, `tope`, `compra_minima`

## Salidas
- `ahorro(gasto)`: pesos que se ahorran de verdad
- `porcentaje_efectivo(gasto)`: qué porcentaje termina siendo en la práctica
- `gasto_optimo()`: el monto a partir del cual el tope empieza a diluir el
  beneficio, o `None` si no hay tope

## Cómo funciona
- Si es una promo de cuotas, el ahorro en pesos es 0: financia, no descuenta.
- Si el gasto no llega a `compra_minima`, el ahorro es 0. No es "un poco menos":
  es nada.
- Se aplica el porcentaje y, si hay `tope`, se corta ahí.

## Casos borde
| Caso | Qué tiene que pasar |
|---|---|
| Gasto por debajo del mínimo | 0, no un ahorro proporcional |
| Gasto muy por encima del tope | El ahorro se queda en el tope y el % efectivo cae |
| `tope` es `None` | Puede significar "sin tope" o "no informado": lo decide `limites_conocidos`, no esta función |
| `valor` es `None` | 0; no se inventa un porcentaje |
| Promo de cuotas | 0 en pesos; el beneficio es financiero |

## Lo que no hace
- No decide si mostrar "sin tope". Eso lo decide `limites_conocidos` y se
  resuelve en la vista: ver [fuentes.md](fuentes.md).
- No suma promos entre sí. La acumulación depende de reglas de cada banco que
  las fuentes no publican.
- No descuenta el tope ya consumido en el mes: eso vive solo en el navegador.

## Verificación
- Pruebas: `pruebas/test_modelo.py`
- Comando: `python -m herramientas.verificar`
- Qué mirar además: si tocaste la versión de Python, tocá también la de
  `docs/app.js`. Están duplicadas a propósito y sin nada que las sincronice:
  ver [../planes/deuda-tecnica.md](../planes/deuda-tecnica.md).

## Relacionado
- [ARQUITECTURA.md](../../ARQUITECTURA.md)
- [../convenciones-frontend.md](../convenciones-frontend.md)
