# Al súper hoy

Promociones de supermercados vigentes en **Santa Fe capital**, con el dato que
realmente decide la compra: si es descuento o reintegro, cuál es el tope y cuál
es la compra mínima.

No es una lista de porcentajes. Un 20% con tope de $25.000 rinde 20% solo hasta
los $125.000; de ahí en más el porcentaje efectivo se derrumba. Y una promo con
mínimo de $100.000 no sirve para una compra de $40.000. La app calcula eso.

## Cómo funciona

```
fuentes  ->  filtro de zona  ->  detalle  ->  fusión  ->  docs/datos/promos.json  ->  web
```

Una vez por día, GitHub Actions corre `python -m ingesta.main`, que:

1. **Lee las fuentes** de forma independiente. Si una falla, las demás siguen.
2. **Filtra por zona** contra `datos/comercios-santa-fe.yml`. Las promos son
   nacionales; ese registro es lo que las vuelve relevantes para la ciudad.
3. **Pide el detalle** solo de las promos que pasaron el filtro — ahí están el
   tope y la compra mínima. Bajar de ~380 a ~70 detalles es lo que hace que el
   proceso sea rápido y liviano.
4. **Fusiona** las promos repetidas entre fuentes, quedándose con el dato más
   completo de cada una.
5. **Compara** contra la corrida anterior y registra qué cambió.

El resultado se commitea como JSON y GitHub Pages lo sirve. Cero servidores,
cero costo, cero tokens de LLM.

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

## Correr localmente

```bash
pip install -r requirements.txt
python -m ingesta.main
python -m http.server 8765 --directory docs
```

Y entrar a <http://localhost:8765>. Abrir `docs/index.html` con doble clic no
funciona: el navegador bloquea la lectura del JSON desde `file://`.

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
