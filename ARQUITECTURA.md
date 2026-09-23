<!-- ultima_verificacion: 2026-09-20 -->
# Arquitectura

Qué pieza hace qué, en qué orden, y por qué está partido así. Las reglas cortas
están en [AGENTS.md](AGENTS.md); acá está el porqué de cada una.

## El flujo, de punta a punta

```
fuentes  ->  filtro de zona  ->  detalle  ->  fusión  ->  docs/datos/promos.json  ->  web
```

Una vez por día, GitHub Actions corre `python -m ingesta.main`:

1. **Lee cada fuente por separado.** Si una falla, las demás siguen y la app
   muestra cuál falló.
2. **Filtra por zona** contra `datos/comercios-santa-fe.yml`.
3. **Pide el detalle** solo de las que pasaron el filtro: ahí están el tope y la
   compra mínima. Bajar de ~380 a ~70 detalles es lo que hace que el proceso sea
   rápido y liviano, y lo que hace que golpear a MODO sea razonable.
4. **Fusiona** las promos repetidas entre fuentes, quedándose con el dato más
   completo de cada una.
5. **Compara** contra la corrida anterior y registra qué cambió.

El resultado se commitea como JSON y GitHub Pages lo sirve. Cero servidores,
cero costo, cero tokens de LLM.

## Las capas

| Capa | Módulo | Qué sabe | Qué no puede hacer |
|---|---|---|---|
| 0 | `ingesta/modelo.py` | Qué es una promo y cómo se calcula el ahorro | Nada del mundo exterior |
| 1 | `ingesta/zona.py` | Qué comercios son de Santa Fe capital | Pedir datos |
| 2 | `ingesta/fuentes/` | Cómo se lee cada fuente y cómo se traduce | Decidir qué se publica |
| 3 | `ingesta/main.py` | El orden del proceso y qué se escribe | Parsear HTML o JSON de una fuente |

Un módulo solo importa capas más bajas que la suya. Lo verifica
`pruebas/test_estructura.py::test_ningun_modulo_importa_una_capa_mas_alta`.

**Por qué.** La capa 0 es la que decide lo que el usuario ve como ahorro, y es
la que tiene que poder probarse con números a mano. Si el modelo pudiera pedir
datos, probarlo pasaría a depender de que MODO esté arriba.

## La red vive en un solo lugar

`requests` y `bs4` solo se importan dentro de `ingesta/fuentes/`. El
orquestador abre la sesión con `fuentes.sesion()` y la pasa; nunca importa la
librería HTTP.

De eso salen tres cosas: el `User-Agent` del proyecto se declara una sola vez,
las pruebas pueden prohibir los sockets sin romper nada
(`pruebas/conftest.py`), y agregar una fuente no requiere tocar ninguna otra
capa.

## El contrato de una fuente

Cada módulo de `ingesta/fuentes/` que expone `listar` es una fuente, y por eso
tiene que:

- declarar `NOMBRE`: la etiqueta que ve el usuario en la pestaña Fuentes;
- exponer `listar(sesion=None)`;
- levantar el `ErrorFuente` compartido ante cualquier fallo de red o de formato.

**Por qué el error compartido.** `main` degrada fuente por fuente atrapando ese
tipo. Una excepción propia de la fuente se le escapa y tumba la corrida entera,
que es exactamente lo que el diseño quiere evitar.

Los módulos de `fuentes/` que no tienen `listar` no son fuentes: son funciones
puras. `pruebas/test_estructura.py::test_cada_fuente_cumple_el_contrato` importa
cada uno y verifica el contrato sobre el módulo real, no sobre el texto.

## Mitad con red, mitad pura

`modo.py` pide; `modo_traduccion.py` traduce. La costura no es estética: la
traducción es donde se decide el tipo, el valor, el tope y el nombre del
comercio —todo lo que el usuario ve— y partida así se prueba entera con una
card escrita a mano, sin abrir un socket.

Cuando un archivo pasa de 300 líneas, esa es la costura por donde parte.

## "Sin tope" no es lo mismo que "no informado"

`Promo.limites_conocidos` distingue las dos cosas. MODO publica los límites en
la página de detalle; Banco Santa Fe no los publica en su listado.

Cuando ninguna fuente los publica, la app dice **"Ahorrás hasta $X"** en vez de
prometer un número. Mostrar "sin tope" ahí sería mentir, y es el error que hace
perder plata en la caja.

En la fusión alcanza con que **una** fuente publique los límites para poder
afirmarlos.

## El filtro de zona

La API de MODO es nacional y no publica las sucursales de cada promo, así que
la relevancia geográfica no se puede deducir de los datos: hay que declararla.
`datos/comercios-santa-fe.yml` es esa declaración, y se edita a mano.

Un comercio nuevo entra con `confirmado: false` hasta que alguien verifique que
tiene sucursal en la ciudad. Los que la app no reconoce no se descartan en
silencio: quedan listados en la pestaña Fuentes para revisarlos.

`zona.contiene()` compara por palabras completas y contiguas, y la dirección
importa: el nombre del registro tiene que estar dentro del nombre de la promo,
no al revés. Así "Carrefour" reconoce a "Carrefour Express", pero "Carrefour
Market" no se queda con un "Super Market" cualquiera.

La comparación por subcadena suelta ya mezcló comercios en una corrida real
("dia" dentro de "diarco", "vea" dentro de "alvear"): por eso el caso está
fijado en `pruebas/test_zona.py`.

## La identidad de una promo

`Promo.huella()` no incluye el tope ni la compra mínima. Si el banco cambia el
tope, queremos reconocerla como la misma promo y reportar el cambio, no darla
por terminada e inventar una nueva. De ahí sale la pestaña Novedades.

## Qué pasa cuando todo falla

Si ninguna fuente responde, la ingesta **no escribe nada** y termina con código
1. El sitio conserva el último dato bueno y avisa solo que está desactualizado.
Es preferible decir que el dato tiene tres días a mostrarlo como si fuera de hoy.

## El sitio

`docs/` es el sitio publicado, no documentación: HTML, CSS y un `app.js` sin
build ni dependencias. Lee `docs/datos/promos.json` y calcula el ahorro en el
navegador. Las convenciones están en
[documentacion/convenciones-frontend.md](documentacion/convenciones-frontend.md).

Las preferencias del usuario (bancos, monto habitual) viven en `localStorage` y
no salen del navegador. Eso es una decisión de privacidad, no una limitación
técnica: ver [documentacion/seguridad.md](documentacion/seguridad.md).

## Límites conocidos

- MODO no publica las sucursales, así que la relevancia geográfica se declara a
  mano y no se deduce de los datos.
- Banco Santa Fe opera en toda la provincia: algunas de sus promos pueden ser de
  otra ciudad. Por eso varios comercios arrancan como `confirmado: false`.
- Quedan fuera Billetera Santa Fe y las promos propias de las cadenas locales.
  No tienen API y necesitan extracción asistida.
- El cálculo de ahorro está escrito dos veces, en Python y en JavaScript. Ver
  [documentacion/planes/deuda-tecnica.md](documentacion/planes/deuda-tecnica.md).
