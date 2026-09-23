"""Presupuestos de tamano, declarados una sola vez.

Un archivo de instrucciones que crece sin limite deja de leerse entero: ni una
persona ni un agente con poco contexto lo recorren completo, y la regla que
importa queda enterrada en la linea 400. El limite no es estetico.

`herramientas/instrucciones.py` los aplica; `pruebas/test_documentos.py` los
prueba. Dos copias de estos numeros serian exactamente el tipo de par "mantener
sincronizado" que este repo saca de encima.
"""

from __future__ import annotations

# AGENTS.md: la superficie de control. Minimo para que un archivo vaciado no
# pase por "corto"; maximo para que siga siendo legible de una sentada.
AGENTS_MIN_BYTES = 1_000
AGENTS_MAX_BYTES = 20_000
AGENTS_MAX_LINEAS = 250

# Los punteros (CLAUDE.md) son eso: punteros. Si crecen, ya son una segunda
# copia de las reglas que se va a desincronizar de AGENTS.md.
PUNTERO_MAX_BYTES = 1_000
PUNTERO_MAX_LINEAS = 20

# Archivos "de tamano agente": un modulo que no entra en una lectura obliga a
# leerlo por pedazos y a adivinar el resto.
CODIGO_MAX_LINEAS = 300
