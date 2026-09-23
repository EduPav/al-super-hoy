<!-- ultima_verificacion: 2026-09-20 -->
# Función: el sitio

## Para qué existe
Es lo único que el usuario ve. Todo lo demás del repo existe para que estas
cuatro vistas digan la verdad.

## Dónde vive
- Código: `docs/index.html`, `docs/app.js`, `docs/estilos.css`
- Datos: `docs/datos/promos.json`
- Convenciones: [../convenciones-frontend.md](../convenciones-frontend.md)

## Las vistas

| Vista | Qué contesta | Función |
|---|---|---|
| **Hoy** | Qué aplica hoy, ordenado por ahorro real | `renderHoy` |
| **Semana** | Qué día conviene hacer la compra grande | `renderSemana` |
| **Novedades** | Qué entró, qué terminó y qué cambió desde la última corrida | `renderNovedades` |
| **Fuentes** | Cuándo se actualizó cada fuente, cuál falló, qué comercios quedaron sin reconocer | `renderFuentes` |

Transversales: la **barra de gasto** (reordena todo por ahorro real), los
**filtros** por banco y medio de pago, y el indicador de **frescura** del dato.

## La calculadora no es una vista
Está en la barra de arriba y atraviesa todas: al cargar un monto, cada tarjeta
muestra cuánto ahorrás, cuándo llegás al tope y cuánto te falta para el mínimo.
Es la diferencia entre la app y una lista de porcentajes.

## Casos borde
| Caso | Qué tiene que pasar |
|---|---|
| `promos.json` no existe o no carga | Mensaje claro, no una pantalla en blanco |
| `limites_conocidos` es `false` | "Ahorrás hasta $X", nunca "sin tope" |
| Una fuente falló en la última corrida | Se dice en la pestaña Fuentes y en el indicador de frescura |
| El dato tiene varios días | Se avisa. Es preferible a mostrarlo como si fuera de hoy |
| La misma promo viene de dos avisos de la misma fuente | La fuente se muestra una sola vez |
| Sin promos para hoy | Estado vacío explícito, no una lista en blanco |

## Lo que no hace
- No pide nada a ningún servidor más que su propio JSON. Sin analytics, sin
  fuentes externas, sin backend.
- No guarda nada fuera de `localStorage`: los bancos del usuario y lo que gasta
  no salen de su navegador.
- No calcula acumulación entre promos.

## Verificación
No hay pruebas automáticas del frontend (está anotado en
[../planes/deuda-tecnica.md](../planes/deuda-tecnica.md)). A mano:

```bash
python -m http.server 8765 --directory docs
```

Y mirar las cuatro vistas en los tres estados: sin datos, con datos, con una
fuente caída. Abrir el HTML con doble clic no funciona.

## Relacionado
- [calculo-de-ahorro.md](calculo-de-ahorro.md)
- [../convenciones-frontend.md](../convenciones-frontend.md)
