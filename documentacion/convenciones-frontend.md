<!-- ultima_verificacion: 2026-09-20 -->
# Convenciones del sitio

`docs/` es el sitio publicado en GitHub Pages. No es documentación: es el
producto. Tres archivos, sin build y sin dependencias.

| Archivo | Qué es |
|---|---|
| `docs/index.html` | El esqueleto: cabecera, barra de gasto, pestañas, un `<section>` por vista |
| `docs/app.js` | Todo el comportamiento |
| `docs/estilos.css` | Todo el estilo |
| `docs/datos/promos.json` | Lo que escribe la ingesta. No se edita a mano |

## Sin build

No hay npm, ni bundler, ni framework. Se edita el archivo y se recarga el
navegador. Esa es la propiedad que hace que el sitio siga funcionando dentro de
dos años sin tocar nada, y la razón para no agregar una dependencia sin un motivo
que valga perderla.

Para verlo:

```bash
python -m http.server 8765 --directory docs
```

Abrir `docs/index.html` con doble clic no funciona: el navegador bloquea la
lectura del JSON desde `file://`.

## Cómo está organizado `app.js`

En este orden, y conviene mantenerlo:

1. Constantes y el estado (`estado`: datos, preferencias, vista actual).
2. Preferencias (`leerPrefs`, `guardarPrefs`).
3. Cálculo (`ahorro`, `porcentajeEfectivo`, `aplicaEnDia`, `vigente`).
4. Formato (`texto`, `fechaCorta`, `pesos`).
5. Selección y orden (`promosVisibles`, `ordenar`).
6. Render: una función `renderX` por vista, y `render()` que las llama.
7. Controles y arranque (`conectarControles`, `iniciar`).

Cada `renderX` escribe en su `<section>` y no toca las otras. Si una vista nueva
necesita datos que no están en `promos.json`, el cambio empieza en la ingesta,
no acá.

## Reglas

- **Los tres estados siempre.** Sin datos, con datos y con una fuente caída.
  La pestaña Fuentes existe justamente para mostrar el tercero.
- **No afirmar un límite que no conocemos.** Si `limites_conocidos` es `false`,
  se dice "Ahorrás hasta $X", nunca "sin tope". Es la regla que más plata le
  ahorra al usuario y la que más fácil se rompe al refactorizar una tarjeta.
- **El orden es por ahorro real**, no por el porcentaje anunciado. Con un monto
  cargado, la lista se reordena.
- **Nada del usuario sale del navegador.** `localStorage` y nada más: ni
  analytics, ni fuentes remotas, ni pedidos a otro dominio. Ver
  [seguridad.md](seguridad.md).
- **Castellano rioplatense**, igual que el resto del repo: "ahorrás", "ponés".
- **Sin acentos en el código, con acentos en lo que se muestra.** Los nombres de
  funciones y variables van en ASCII; los textos visibles, bien escritos.

## El cálculo está escrito dos veces

`ahorro()` vive en `docs/app.js` y en `ingesta/modelo.py`. Es duplicación real y
está anotada en [planes/deuda-tecnica.md](planes/deuda-tecnica.md).

Mientras siga así: **si tocás una, tocá la otra**, y agregá el caso en
`pruebas/test_modelo.py`. La versión de Python es la que tiene pruebas, así que
es la que manda cuando las dos discrepan.
