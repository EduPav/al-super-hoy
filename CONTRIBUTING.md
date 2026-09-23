# Cómo contribuir

Un proyecto chico para Santa Fe capital. El proceso es corto a propósito.

## El camino

- Quien mantiene el repo commitea directo a `main`.
- Desde afuera: forkeá, trabajá en una rama y abrí un Pull Request a `main`.
- Para un arreglo chico no hace falta pedir permiso. Para algo grande, abrí
  primero un issue: puede que ya esté decidido que no va.

## El único gate

```bash
pip install -r requirements-dev.txt
python -m herramientas.verificar
```

Corre el chequeo de instrucciones, `ruff` y las pruebas. Sin red y sin
credenciales: si pasa en tu máquina, pasa en el PR. Es lo mismo que corre CI.

## Antes de abrir el PR

- Leé [AGENTS.md](AGENTS.md): son las reglas del repo, todas, en un archivo.
- Un cambio coherente por PR. Solo los archivos que el cambio pide.
- Pruebas y documentación en el mismo commit que el código.
- La plantilla del PR pregunta qué comandos corriste. Contestala con la verdad,
  incluido lo que no corriste y por qué.

## El PR más fácil para empezar

Falta un supermercado de la ciudad. Se agrega a `datos/comercios-santa-fe.yml`
con `confirmado: false`; el paso a paso está en
[documentacion/flujos-de-trabajo.md](documentacion/flujos-de-trabajo.md#agregar-un-comercio-al-registro).

## Lo que no entra

- Credenciales, tokens, `.env`, cookies. El repo es público y el historial
  queda aunque después se borre el archivo:
  [documentacion/seguridad.md](documentacion/seguridad.md).
- Datos personales, tuyos o de otra persona: bancos reales, dirección, cuánto
  gastás.
- Fuentes que exijan iniciar sesión. Solo endpoints y páginas públicas.

## Licencia

Al abrir un PR aceptás que tu aporte se publique bajo la licencia MIT del
proyecto ([LICENSE](LICENSE)).
