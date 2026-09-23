<!-- ultima_verificacion: 2026-09-20 -->
# Planes

| Carpeta | Qué hay |
|---|---|
| `activos/` | Lo que se está haciendo ahora |
| `completados/` | Lo que se terminó y se validó |
| [deuda-tecnica.md](deuda-tecnica.md) | Lo que sabemos que está mal y decidimos no arreglar todavía |

## Cuándo escribir un plan

Cuando el cambio no es trivial: toca más de un archivo, cambia una decisión de
diseño, o va a llevar más de una sesión. Un cambio chico no necesita plan; un
plan que nadie lee es peor que no tenerlo.

El plan existe para que el trabajo sobreviva a que se corte la sesión. Si hay
que reconstruir el contexto leyendo el diff, el plan falló.

## Formato

Un archivo por plan, `activos/<nombre-corto>.md`:

```markdown
<!-- ultima_verificacion: AAAA-MM-DD -->
# <Qué se va a hacer>

## Por qué
El problema, no la solución.

## Qué se cambia
- archivo o módulo -> qué le pasa

## Qué NO se cambia
Lo tentador que queda afuera de este cambio.

## Cómo se verifica
El comando, y lo que ninguna prueba puede ver.

## Estado
- [ ] paso
- [x] paso hecho
```

Cuando se valida, se mueve a `completados/` con el estado final. No se borra:
la próxima vez que alguien se pregunte por qué algo está así, la respuesta está
ahí.
