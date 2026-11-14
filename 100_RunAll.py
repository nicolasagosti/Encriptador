#!/usr/bin/env python3
"""Ejecuta paso1, paso2 y paso3 en orden. Se detiene si alguno falla.

Uso:
    python3 run_all.py "texto para el paso 3"
    run_all.exe "texto para el paso 3"
"""

import argparse
import sys
import time
from typing import Callable

import paso1
import paso1Modificado
import paso2
import paso3


def ejecutar(nombre: str, funcion: Callable[[], None]) -> None:
    print(f"\n▶ Ejecutando {nombre}...")
    inicio = time.perf_counter()
    funcion()
    print(f"✔ {nombre} OK ({time.perf_counter() - inicio:.2f}s)")


def main() -> int:

    pasos: list[tuple[str, Callable[[], None]]] = [
        ("paso1", paso1Modificado.main),
        ("paso2", paso2.main),
        ("paso3", paso3.main)
    ]

    for nombre, funcion in pasos:
        try:
            ejecutar(nombre, funcion)
        except Exception as e:
            print(f"✘ {nombre} falló: {e}", file=sys.stderr)
            return 1

    print("\n✅ Todos los pasos terminaron correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())