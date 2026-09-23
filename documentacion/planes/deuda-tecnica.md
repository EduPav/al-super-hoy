<!-- ultima_verificacion: 2026-09-20 -->
# Deuda técnica

Lo que sabemos que está mal y decidimos no arreglar todavía. Se anota acá cuando
se descubre o cuando se crea, en el mismo cambio.

Una deuda anotada es una decisión; una deuda sin anotar es una trampa para el
próximo que pase.

## Abierta

| Qué | Por qué duele | Cómo se resolvería | Prioridad |
|---|---|---|---|
| El cálculo de ahorro está escrito dos veces: `ingesta/modelo.py` y `docs/app.js` | Nada las sincroniza. Si divergen, el orden de la lista y el número que ve el usuario dejan de coincidir con lo que la ingesta calculó | Que la ingesta escriba el ahorro precalculado para varios montos, o compartir el cálculo compilando una sola fuente. Las dos opciones cuestan más que la duplicación mientras el cálculo sea esta fórmula | Media |
| El frontend no tiene ninguna prueba | Las cuatro vistas y los tres estados (vacío, con datos, fuente caída) se verifican a ojo. La regla de "no afirmar un límite que no conocemos" vive en una rama de `tarjetaPromo` sin nada que la sostenga | Pruebas de render sin build (un runner chico sobre jsdom), o mover la decisión de qué texto mostrar a la ingesta, donde ya hay pruebas | Media |
| Banco Santa Fe no publica tope ni compra mínima en su listado | Sus promos exclusivas se muestran siempre como "no informado", que es honesto pero poco útil | Los valores viven en un diálogo que se carga aparte; habría que pedirlo por promo, con el costo de red que eso implica | Baja |
| El parseo de Banco Santa Fe depende de la estructura `h4` + `p` | Un rediseño de la página lo rompe entero, y el fallo se ve como "0 promos" | Sin API no hay forma robusta. Mitigado: un 200 que no reconoce nada levanta `ErrorFuente` en vez de reportar cero | Baja |
| `datos/estado-anterior.json` guarda una sola corrida | No hay historia: no se puede responder "cuándo cambió este tope" | Un archivo append-only por mes, o directamente la historia de git de ese archivo | Baja |
| Quedan fuera Billetera Santa Fe y las promos propias de las cadenas locales | Son promos reales de la ciudad que la app no muestra | No tienen API y necesitan extracción asistida. Es la segunda etapa del proyecto | Media |
| `datos/cache/` no se limpia sola | Crece con un archivo por promo vista; nadie lo borra | Borrar lo más viejo que el `max_edad_horas` al terminar la ingesta | Baja |

## Resuelta

| Qué era | Cómo se resolvió |
|---|---|
| Falsos positivos al comparar nombres de comercio por subcadena | `zona.contiene()` compara palabras completas y contiguas, con la dirección fijada; los casos reales quedaron en `pruebas/test_zona.py` |
| `ingesta/fuentes/modo.py` mezclaba la red con la traducción, en 308 líneas | Partido en `modo.py` (red) y `modo_traduccion.py` (puro). La traducción se prueba entera sin abrir un socket |
| El `User-Agent` estaba escrito en cada fuente | Se declara una sola vez en `ingesta/fuentes/__init__.py`, verificado por `pruebas/test_estructura.py::test_el_user_agent_se_declara_una_sola_vez` |
| Cada fuente definía su propio `ErrorFuente` | Uno compartido; `main` degrada fuente por fuente atrapando ese tipo |
| El repo no tenía ninguna prueba | Suite de pytest sin red, con los sockets bloqueados en `pruebas/conftest.py` |
| Las reglas del repo vivían solo en prosa | `python -m herramientas.instrucciones` y `pruebas/test_estructura.py` las hacen cumplir |
