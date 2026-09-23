<!-- ultima_verificacion: 2026-09-20 -->
# Verificación

Qué revisa cada gate, qué necesita para correr y cómo salir cuando falla.
La tabla de qué regla hace cumplir cada uno está en
[AGENTS.md](../AGENTS.md#control-mecánico).

## El gate canónico

```bash
python -m herramientas.verificar
```

Corre tres cosas en orden y corta en la primera que falle:

1. `python -m herramientas.instrucciones` — la superficie de instrucciones.
2. `ruff check .` — estilo, imports, variables sin usar, `print()` fuera de lugar.
3. `pytest` — las pruebas.

**Sin red y sin credenciales.** Las pruebas tienen los sockets bloqueados
(`pruebas/conftest.py`), así que el resultado es el mismo en tu máquina, en CI y
con MODO caído. Tarda unos segundos: no hay razón para no correrlo.

Necesita `pip install -r requirements-dev.txt`. Si falta `pytest` o `ruff`, el
comando lo dice con el `pip install` exacto en vez de fallar con un rastro.

## Qué NO cubre

Ninguna prueba puede ver si una fuente cambió su HTML esta mañana. Después de
tocar una fuente o el filtro de zona hay que correr la ingesta de verdad:

```bash
python -m ingesta.main
```

y mirar el mapeo comercio por comercio. Que el total baje no significa que esté
mal, y que suba no significa que esté bien.

## El chequeo de instrucciones

```bash
python -m herramientas.instrucciones
```

Solo biblioteca estándar: corre en un clon recién bajado, antes de instalar
nada. Por eso es el primer gate y un job propio en CI.

Revisa:

| Qué | Por qué |
|---|---|
| `AGENTS.md` entre 1 KB y 20 KB, hasta 250 líneas | Un archivo de instrucciones que no se lee entero deja la regla que importa en la línea 400 |
| Las secciones que cargan una regla siguen existiendo | Si desaparece la sección, se perdió la regla aunque el archivo siga ahí |
| La autoridad de las instrucciones nombra qué manda y qué es un dato leído | Es la defensa contra una página scrapeada que trae texto con forma de orden |
| La regla de secretos prohíbe, en un mismo enunciado, cada cosa y cada superficie de fuga | Con dos frases sueltas, una oración que dice lo contrario alcanzaba para dar la regla por cumplida |
| `CLAUDE.md` apunta a `AGENTS.md` y no pasa de 20 líneas | Si crece, ya es una segunda copia de las reglas que se va a desincronizar |
| `documentacion/seguridad.md` entra a `AGENTS.md` por ancla, y esa ancla existe | Renumerar la sección rompe el link fuerte en vez de dejar al lector arriba de todo |
| Cada prueba que la tabla de control cita existe y define esa función | Una tabla que cita pruebas borradas promete un control que no hay |
| Todos los links relativos y las anclas resuelven | GitHub sirve el archivo igual, así que un link roto se lee como si funcionara |
| Los comandos documentados apuntan a módulos que existen | Un comando renombrado deja la documentación mandando a la nada |
| Los gates marcados `[CI]` están nombrados en el README y en los flujos | Ahí es donde la próxima persona los busca |
| CI corre esos gates, en un `run:` de verdad | Ver abajo |
| Git ignora `.env` y `datos/cache/`, y no hay ningún `.env` versionado | El repo es público y el historial queda |
| Cada documento declara su `ultima_verificacion` | Para saber desde cuándo nadie lo mira |

### Cómo se reconoce que CI corre un gate

No alcanza con que el texto del comando aparezca en el workflow. `run:` se
reconoce **solo a nivel de paso**: un `run` que es un input dentro de `with:` no
ejecuta nada, y una línea dentro de un heredoc tampoco. El comando tiene que
empezar la línea, no estar contenido en ella. Además se rechaza un `if: false`,
porque un job apagado sigue declarando el paso.

Los tres casos están fijados en `pruebas/test_documentos.py`.

### OMITIDO no es verde

Un chequeo que no se puede evaluar —no hay árbol de git, git no está
instalado— se reporta como `OMITIDO`, nunca como aprobado. Un verde que no midió
nada es peor que un rojo: nadie lo vuelve a mirar.

## El preflight

```bash
python -m herramientas.doctor
```

Contesta "¿por qué me falla?" antes de que falle: versión de Python,
dependencias instaladas, el registro de comercios en su lugar, si ya existe
`docs/datos/promos.json`. Cada fallo viene con el comando exacto que lo arregla.

## Las pruebas

| Archivo | Qué fija |
|---|---|
| `pruebas/test_modelo.py` | El cálculo de ahorro: tope, compra mínima, cuotas, identidad de una promo |
| `pruebas/test_zona.py` | El filtro de zona y los falsos positivos por subcadena |
| `pruebas/test_fuente_modo.py` | La traducción de una card de MODO al modelo |
| `pruebas/test_fuente_banco_santa_fe.py` | El parseo del listado, con una sesión falsa |
| `pruebas/test_fusion.py` | La fusión entre fuentes y el cálculo de novedades |
| `pruebas/test_estructura.py` | Las capas, el contrato de fuente, los tamaños, el registro |
| `pruebas/test_documentos.py` | La lógica de los chequeos: el que controla también se prueba |

### Fixtures escritos a mano

No entran volcados crudos de una API ni de una página al repo: es público y esos
volcados pueden traer identificadores de sesión o datos de otras personas. Los
fixtures son mínimos y escritos a mano, con los campos que el parser mira.
Envejecen mejor, además: un volcado real se vuelve incomprensible en un mes.

### Si una prueba intenta salir a la red

Falla con `RedProhibida`. No la destrabes: pasale una sesión falsa como hacen
`pruebas/test_fuente_banco_santa_fe.py` o un fixture escrito a mano. Una prueba
que sale a la red anda en tu máquina, falla en CI, y golpea una fuente pública
cada vez que alguien corre el suite.

## CI

`.github/workflows/verificar.yml` corre en cada push y cada pull request a
`main`, en dos jobs paralelos:

- **instrucciones** — `python -m herramientas.instrucciones`, sin instalar nada.
  Que sea un job propio es la prueba de que el chequeo no depende del entorno.
- **verificar** — `python -m herramientas.verificar`, con las dependencias
  instaladas.

`.github/workflows/actualizar.yml` es otra cosa: es la ingesta diaria, la que
sale a la red y commitea `docs/datos/promos.json`. Si falla, no escribe nada y
el sitio conserva el último dato bueno.

## Pre-commit (opcional)

`.pre-commit-config.yaml` corre ruff y un detector de secretos sobre lo que
estás por commitear. Se instala una vez:

```bash
pip install pre-commit
pre-commit install
```

No reemplaza al gate: es la red que atrapa lo obvio antes.
