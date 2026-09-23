<!-- ultima_verificacion: 2026-09-20 -->
# Flujos de trabajo

Los comandos y el checklist de cada tipo de tarea. Las reglas están en
[AGENTS.md](../AGENTS.md); lo que revisa cada gate, en
[verificacion.md](verificacion.md).

## Comandos

| Para | Comando |
|---|---|
| Ver si el entorno está listo | `python -m herramientas.doctor` |
| Chequear la superficie de instrucciones | `python -m herramientas.instrucciones` |
| El gate canónico, antes de dar algo por bueno | `python -m herramientas.verificar` |
| Correr la ingesta completa (usa red) | `python -m ingesta.main` |
| Listar los comercios que publica MODO hoy (usa red) | `python -m ingesta.explorar` |
| Ver el sitio | `python -m http.server 8765 --directory docs` |
| Instalar todo | `pip install -r requirements-dev.txt` |
| Solo lo que necesita la ingesta en producción | `pip install -r requirements.txt` |

## Arrancar de cero

```bash
pip install -r requirements-dev.txt
python -m herramientas.doctor
python -m herramientas.verificar
python -m ingesta.main
python -m http.server 8765 --directory docs
```

## Cambiar código

- [ ] Leer [AGENTS.md](../AGENTS.md) y, si el cambio es estructural,
      [ARQUITECTURA.md](../ARQUITECTURA.md).
- [ ] Leer la ficha de la función en [funciones/](funciones/).
- [ ] Si no es trivial, dejar un plan en `planes/activos/`.
- [ ] Hacer el cambio más chico que resuelva el problema.
- [ ] Agregar o actualizar pruebas.
- [ ] `python -m herramientas.verificar`.
- [ ] Actualizar la documentación en el mismo cambio.
- [ ] Mover el plan a `planes/completados/`.

## Arreglar un bug

- [ ] Escribir primero la prueba que lo reproduce.
- [ ] Verla fallar. Una prueba que nunca falló no prueba nada.
- [ ] Arreglar.
- [ ] `python -m herramientas.verificar`.
- [ ] Si el comportamiento cambió, actualizar la ficha de la función.

## Agregar una fuente

- [ ] Confirmar que la página o el endpoint es **público**: accesible sin
      iniciar sesión. No scrapear detrás de un login ni reusar la sesión del
      usuario.
- [ ] Crear `ingesta/fuentes/<fuente>.py` con `NOMBRE`, `listar(sesion=None)` y
      `ErrorFuente` compartido.
- [ ] Si hay parseo, partirlo: la mitad con red en `<fuente>.py`, la traducción
      pura en `<fuente>_traduccion.py`. Esa es la mitad que se prueba.
- [ ] No declarar un `User-Agent` propio: ya está en `ingesta/fuentes/__init__.py`.
- [ ] Si la fuente no publica tope ni compra mínima, dejar `limites_conocidos`
      en `False`.
- [ ] Sumar la fuente en `ingesta/main.py` con su propio `try`: una fuente que
      falla no puede tumbar a las demás.
- [ ] Pruebas con una sesión falsa y fixtures escritos a mano. Nunca un volcado
      crudo de la respuesta real.
- [ ] Ficha en `funciones/fuentes.md` y fila en el mapa de
      [ARQUITECTURA.md](../ARQUITECTURA.md).
- [ ] `python -m herramientas.verificar` y después `python -m ingesta.main`.

## Agregar un comercio al registro

- [ ] `python -m ingesta.explorar` para ver los nombres que publica MODO hoy, o
      la lista "No reconocidos" de la pestaña Fuentes.
- [ ] Agregarlo a `datos/comercios-santa-fe.yml` con `confirmado: false`.
- [ ] Los alias van en `alias:`; el nombre principal es el que ve el usuario.
- [ ] `python -m ingesta.main` y revisar el mapeo comercio por comercio. Que el
      total baje no significa que esté mal.
- [ ] Cuando verifiques que tiene sucursal en la ciudad, `confirmado: true`.

## Tocar el sitio

- [ ] Leer [convenciones-frontend.md](convenciones-frontend.md).
- [ ] `python -m http.server 8765 --directory docs` y mirar el resultado. Abrir
      el HTML con doble clic no funciona.
- [ ] Verificar los tres estados: sin datos, con datos, con una fuente caída.

## Actualizar documentación

- [ ] Actualizar solo el lugar canónico (ver la tabla en
      [AGENTS.md](../AGENTS.md#dónde-se-documenta-cada-cambio)).
- [ ] Nunca duplicar: enlazar.
- [ ] Actualizar el `<!-- ultima_verificacion: AAAA-MM-DD -->` del encabezado.

## Abrir un cambio para revisión

- [ ] Un cambio coherente por vez.
- [ ] `python -m herramientas.verificar` antes de abrirlo.
- [ ] Documentación actualizada en el mismo cambio.
- [ ] Solo los archivos que el trabajo pide. Nada de mejoras al pasar.

`.github/PULL_REQUEST_TEMPLATE.md` y
`.github/ISSUE_TEMPLATE/tarea-para-agente.md` piden esa evidencia sin que haya
que abrir este archivo. Son formularios, no un segundo reglamento: las reglas
viven acá y en AGENTS.md. Si una plantilla repitiera una regla, esa copia
quedaría pegada en todos los issues viejos y no habría forma de corregirla.
