"""Utilidad de mantenimiento: lista los comercios que hoy publica MODO.

Sirve para revisar el registro de zona cuando aparecen nombres nuevos.
Uso:  python -m ingesta.explorar
"""

from collections import Counter

from .fuentes import modo


def main() -> None:
    cards = modo.listar()
    comercios = Counter()
    for card in cards:
        p = modo.a_promo(card)
        comercios[p.comercio] += 1
    print(f"{len(cards)} promos, {len(comercios)} comercios distintos\n")
    for nombre, n in sorted(comercios.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{n:3d}  {nombre}")


if __name__ == "__main__":
    main()
