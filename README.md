# Al súper hoy

Promociones de supermercados vigentes en **Santa Fe capital**, con el dato que
realmente decide la compra: si es descuento o reintegro, cuál es el tope y cuál
es la compra mínima.

No es una lista de porcentajes. Un 20% con tope de $25.000 rinde 20% solo hasta
los $125.000; de ahí en más el porcentaje efectivo se derrumba. Y una promo con
mínimo de $100.000 no sirve para una compra de $40.000. La app calcula eso.

## Correr localmente

```bash
pip install -r requirements-dev.txt
python -m herramientas.doctor        # el entorno está listo?
python -m ingesta.main               # baja las promos y escribe docs/datos/promos.json
python -m http.server 8765 --directory docs
```

Y entrar a <http://localhost:8765>. Abrir `docs/index.html` con doble clic no
funciona: el navegador bloquea la lectura del JSON desde `file://`.

Antes de dar un cambio por bueno:

```bash
python -m herramientas.verificar
```

Corre el chequeo de instrucciones, ruff y las pruebas. Sin red y sin
credenciales, así que da lo mismo en tu máquina que en CI. El detalle de cada
gate está en [documentacion/verificacion.md](documentacion/verificacion.md).

## Cómo funciona

```
fuentes  ->  filtro de zona  ->  detalle  ->  fusión  ->  docs/datos/promos.json  ->  web
```

Una vez por día, GitHub Actions corre `python -m ingesta.main`, que lee cada
fuente por separado, filtra por el registro de comercios de la ciudad, pide el
detalle solo de las que pasaron el filtro (ahí están el tope y la compra
mínima), fusiona las repetidas y compara contra la corrida anterior.

El resultado se commitea como JSON y GitHub Pages lo sirve. Cero servidores,
cero costo, cero tokens de LLM.

El porqué de cada decisión está en [ARQUITECTURA.md](ARQUITECTURA.md).

### Las fuentes

| Fuente | Qué aporta | Cómo se lee |
|---|---|---|
| **MODO** | El grueso. Agrega las promos de +80 bancos, con tope exacto, compra mínima, días, medios de pago y vigencia. | API REST pública, sin autenticación |
| **Banco Santa Fe** | Las promos locales que MODO no lista (La Gallega, Bacim, Alfa, Beltrán, El Túnel, Kilbel, Alvear). | HTML renderizado en el servidor, parseado con reglas fijas |

Ninguna de las dos es una API contratada ni documentada: son endpoints públicos
que pueden cambiar sin aviso. Por eso la app muestra siempre cuándo se actualizó
por última vez y cuál fuente falló.

### Sin tope vs. no informado

Banco Santa Fe no publica los topes en su listado. Mostrar "sin tope" ahí sería
mentir. La app distingue los dos casos y, cuando el límite no está informado,
dice **"Ahorrás hasta $X"** en vez de prometer el número.

## Funciones

- **Hoy** — qué aplica hoy, ordenado por ahorro real.
- **Semana** — calendario lunes a domingo, para elegir el día de la compra grande.
- **Calculadora** — ponés cuánto vas a gastar y te dice cuánto ahorrás con cada
  promo, cuándo llegás al tope y cuánto te falta para el mínimo.
- **Mis bancos** — filtrás por los que realmente tenés; el resto desaparece.
- **Novedades** — qué entró, qué terminó y qué cambió desde la última corrida.
- **Fuentes** — cuándo se actualizó cada una, cuál falló y qué comercios quedaron
  sin reconocer.

Las preferencias se guardan en `localStorage`: quedan en tu navegador y no se
publican con el sitio.

## Mantenimiento

Lo único que necesita atención humana es el registro de comercios:

```bash
python -m ingesta.explorar    # lista los comercios que publica MODO hoy
```

La pestaña **Fuentes** de la app muestra dos listas para revisar:

- **Sin confirmar** — están en el registro pero no verificaste la sucursal.
  Marcá `confirmado: true` o sacalos.
- **No reconocidos** — tienen promo vigente pero no están en el registro, así
  que la app los ignora. Si alguno está en la ciudad, agregalo.

El paso a paso está en
[documentacion/flujos-de-trabajo.md](documentacion/flujos-de-trabajo.md).

## Si venís a cambiar algo

El repo está armado para que lo trabaje un agente de código sin tener que
adivinar nada:

| Querés | Leé |
|---|---|
| Las reglas del repo, todas | [AGENTS.md](AGENTS.md) |
| Mandar un PR desde afuera | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Cómo está armado y por qué | [ARQUITECTURA.md](ARQUITECTURA.md) |
| El checklist de tu tipo de tarea | [documentacion/flujos-de-trabajo.md](documentacion/flujos-de-trabajo.md) |
| Qué revisa cada gate | [documentacion/verificacion.md](documentacion/verificacion.md) |
| Cómo funciona una pieza en detalle | [documentacion/funciones/](documentacion/funciones/) |
| Qué sabemos que está mal | [documentacion/planes/deuda-tecnica.md](documentacion/planes/deuda-tecnica.md) |

`AGENTS.md` es la única fuente de instrucciones; `CLAUDE.md` solo apunta ahí.
Las reglas que se pueden verificar, se verifican: `python -m herramientas.instrucciones`
chequea la propia documentación (tamaño, secciones, links, anclas, comandos, lo
que CI dice correr) y `pruebas/test_estructura.py` chequea las capas del código.

## Publicar

En **Settings → Pages**, elegir `Deploy from a branch`, rama `main`, carpeta
`/docs`. El workflow ya commitea los datos actualizados a esa rama.

## Límites conocidos

- La API de MODO no publica las sucursales de cada promo, así que la relevancia
  geográfica se declara a mano en el registro y no se deduce de los datos.
- Banco Santa Fe opera en toda la provincia: algunas de sus promos pueden ser de
  Rosario, Rafaela o Reconquista y no de la capital. Por eso varios comercios
  arrancan como `confirmado: false`.
- Quedan fuera **Billetera Santa Fe** y las promos propias de las cadenas
  locales (folletos de Alvear, "Clientazo"). No tienen API y necesitan
  extracción asistida; son la segunda etapa.

## Aviso

Los datos salen de fuentes públicas y pueden tener errores o desactualizarse.
Antes de una compra grande, confirmá en el link de la fuente que trae cada promo.

## Licencia

MIT. Ver [LICENSE](LICENSE).
