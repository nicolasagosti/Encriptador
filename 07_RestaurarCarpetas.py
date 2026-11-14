#!/usr/bin/env python3
"""
Desencripta los backups (.zip AES-256) y los restaura en el Desktop.

- Lee los zips de ~/backups/backups_encriptados/encriptados
- Si hay varios backups de la misma carpeta (tinta_2026-11-03_1738.zip, tinta_2026-11-04_...),
  restaura solo el MÁS RECIENTE.
- No pisa nada: si la carpeta ya existe en el Desktop, la saltea
  (salvo que uses --sobrescribir).
- Extrae primero en una carpeta temporal y recién al final la mueve al Desktop:
  si la contraseña está mal o el zip está corrupto, no queda nada a medias.

Requisitos:
    python -m pip install pyzipper

Uso:
    python restaurar_desktop.py
    python restaurar_desktop.py --sobrescribir
"""
import argparse
import getpass
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import pyzipper
except ImportError:
    sys.exit("Falta la dependencia 'pyzipper'. Instalala con: python -m pip install pyzipper")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ORIGEN = Path.home() / "backups" / "DesktopAZip" 
DESKTOP = Path.home() / "Desktop"

# nombre_2026-11-03_1738.zip  →  ("nombre", "2026-11-03_1738")
PATRON_BACKUP = re.compile(r"^(?P<nombre>.+)_(?P<fecha>\d{4}-\d{2}-\d{2}_\d{4})\.zip$", re.IGNORECASE)

CHUNK_SIZE = 1024 * 1024  # 1 MiB


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desencripta los backups y los restaura en el Desktop.")
    parser.add_argument("--sobrescribir", action="store_true",
                        help="Reemplazar carpetas que ya existan en el Desktop")
    return parser.parse_args()


def ultimos_backups(origen: Path) -> list[Path]:
    """Devuelve el zip más reciente de cada carpeta respaldada."""
    if not origen.is_dir():
        sys.exit(f"❌ No existe la carpeta de backups: {origen}")

    ultimos: dict[str, tuple[str, Path]] = {}
    for zip_path in origen.iterdir():
        m = PATRON_BACKUP.match(zip_path.name)
        if not m or not zip_path.is_file():
            continue
        nombre, fecha = m["nombre"], m["fecha"]
        # La fecha en formato AAAA-MM-DD_HHMM se puede comparar como texto.
        if nombre not in ultimos or fecha > ultimos[nombre][0]:
            ultimos[nombre] = (fecha, zip_path)
    return sorted(path for _, path in ultimos.values())


def pedir_password() -> bytes:
    password = os.environ.get("ZIP_PASSWORD") or getpass.getpass("Contraseña: ")
    return password.encode("utf-8")


def ruta_segura(base: Path, nombre: str) -> Path:
    """Evita 'zip slip': que una entrada como '../../.bashrc' escriba fuera de la carpeta destino."""
    destino = (base / nombre).resolve()
    if base.resolve() not in destino.parents:
        raise ValueError(f"Entrada con ruta peligrosa: {nombre!r}")
    return destino


def extraer(zip_path: Path, destino: Path, password: bytes) -> None:
    """Extrae el zip encriptado en destino, conservando permisos (ej: scripts ejecutables)."""
    with pyzipper.AESZipFile(zip_path) as zf:
        zf.setpassword(password)
        for info in zf.infolist():
            ruta = ruta_segura(destino, info.filename)
            if info.is_dir():
                ruta.mkdir(parents=True, exist_ok=True)
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(ruta, "wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK_SIZE)
            permisos = (info.external_attr >> 16) & 0o777
            if permisos:
                ruta.chmod(permisos)


def mover_al_desktop(tmp: Path, desktop: Path, sobrescribir: bool) -> list[str]:
    """Mueve lo extraído al Desktop. Devuelve los nombres restaurados."""
    restaurados = []
    for item in tmp.iterdir():
        final = desktop / item.name
        if final.exists() or final.is_symlink():
            if not sobrescribir:
                print(f"⏭️  Ya existe en el Desktop, se saltea: {item.name}")
                continue
            shutil.rmtree(final) if final.is_dir() and not final.is_symlink() else final.unlink()
        shutil.move(str(item), final)
        restaurados.append(item.name)
    return restaurados


def restaurar(zip_path: Path, desktop: Path, password: bytes, sobrescribir: bool) -> bool:
    """Restaura un backup. Devuelve True si salió bien."""
    # El temporal va dentro del Desktop para que el move final sea instantáneo (mismo disco).
    with tempfile.TemporaryDirectory(dir=desktop, prefix=".restaurando_") as tmp:
        try:
            extraer(zip_path, Path(tmp), password)
        except RuntimeError as e:
            motivo = "contraseña incorrecta" if "password" in str(e).lower() else e
            print(f"❌ {zip_path.name}: {motivo}")
            return False
        except (OSError, ValueError, pyzipper.BadZipFile) as e:
            print(f"❌ {zip_path.name}: {e}")
            return False

        for nombre in mover_al_desktop(Path(tmp), desktop, sobrescribir):
            print(f"✅ Restaurado: {desktop / nombre}  (desde {zip_path.name})")
    return True


def restaurar_todos(backups: list[Path], desktop: Path, password: bytes, sobrescribir: bool) -> int:
    """Restaura todos los backups. Devuelve cuántos fallaron."""
    desktop.mkdir(parents=True, exist_ok=True)
    return sum(not restaurar(z, desktop, password, sobrescribir) for z in backups)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    backups = ultimos_backups(ORIGEN)
    if not backups:
        print(f"No se encontraron backups en {ORIGEN}")
        return 1

    print(f"Se van a restaurar {len(backups)} backups en {DESKTOP}\n")
    errores = restaurar_todos(backups, DESKTOP, pedir_password(), args.sobrescribir)
    print(f"\nListo: {len(backups) - errores} restaurados, {errores} con error.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())