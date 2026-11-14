#!/usr/bin/env python3
"""
Borra todas las carpetas del escritorio (no toca los archivos sueltos).

Seguridad:
  - Por defecto es una SIMULACIÓN: solo muestra qué borraría.
  - Para borrar de verdad hay que pasar --borrar y escribir BORRAR para confirmar.
  - Solo borra carpetas que tengan un backup .zip en DESTINO (nombre_<fecha>.zip).
    Para saltear ese chequeo: --sin-backup.
  - Los enlaces simbólicos (ej: musica → /mnt/compartido) nunca se siguen:
    se saltean, así no se borra el contenido al que apuntan.

Uso:
    python borrar_carpetas_desktop.py                  # simulación
    python borrar_carpetas_desktop.py --borrar         # borra (pide confirmación)
    python borrar_carpetas_desktop.py --borrar --sin-backup
"""
import argparse
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DESKTOP = Path.home() / "Desktop"
PALABRA_CONFIRMACION = "BORRAR"


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Borra todas las carpetas del escritorio.")
    parser.add_argument("--borrar", action="store_true", help="Borrar de verdad (sin esto es simulación)")
    parser.add_argument("--sin-backup", action="store_true", help="No exigir backup previo de cada carpeta")
    return parser.parse_args()


def validar_desktop(desktop: Path) -> None:
    """Evita desastres si la ruta está mal configurada (ej: que apunte al home o a /)."""
    if not desktop.is_dir():
        sys.exit(f"❌ No existe el escritorio: {desktop}")
    if desktop.resolve() in (Path("/"), Path.home().resolve()):
        sys.exit(f"❌ Ruta peligrosa, no se borra nada: {desktop}")


def tiene_backup(carpeta: Path, destino: Path) -> bool:
    return any(destino.glob(f"{carpeta.name}_*.zip"))


def elegir_carpetas(desktop: Path, exigir_backup: bool) -> list[Path]:
    """Devuelve las carpetas a borrar, informando las que se saltean y por qué."""
    a_borrar = []
    for elemento in sorted(desktop.iterdir()):
        if elemento.is_symlink():
            print(f"⏭️  Salteado (enlace): {elemento.name}")
        elif not elemento.is_dir():
            continue  
        else:
            a_borrar.append(elemento)
    return a_borrar


def borrar(carpetas: list[Path]) -> int:
    """Borra las carpetas. Devuelve cuántas fallaron."""
    errores = 0
    for carpeta in carpetas:
        try:
            shutil.rmtree(carpeta)
            print(f"✅ Borrada: {carpeta.name}")
        except OSError as e:
            errores += 1
            print(f"❌ No se pudo borrar {carpeta.name}: {e}")
    return errores


def simular(carpetas: list[Path]) -> None:
    print(f"\n[SIMULACIÓN] Se borrarían {len(carpetas)} carpetas:")
    print("\n".join(f"  🗑️  {c}" for c in carpetas))
    print("\nPara borrar de verdad: python borrar_carpetas_desktop.py --borrar")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    validar_desktop(DESKTOP)
    carpetas = elegir_carpetas(DESKTOP, exigir_backup=not args.sin_backup)
    borrar(carpetas)
    return 


if __name__ == "__main__":
    sys.exit(main())