#!/usr/bin/env python3
# ENCRIPTAR:  carpeta ──zip──► bytes ──cifrar con clave──► archivo.enc
#                                         ▲
#                         contraseña + salt ──KDF──► clave
#
# DESENCRIPTAR: archivo.enc ──► separar salt ──► misma clave ──► descifrar ──► unzip
import os
import zipfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DESKTOP = Path.home() / "Desktop"                           # /home/mechicush/Desktop
DESTINO = Path.home() / "backups" / "backups_encriptados"   # /home/mechicush/backups/backups_encriptados

# Carpetas que no se incluyen en el backup (se regeneran solas).
EXCLUIR = {
    "node_modules", ".next",               # Node / Next.js
    "venv", ".venv", "__pycache__",        # Python
    "target", "build", "dist",             # Java / builds
    ".git",                                # quitalo si querés backupear el historial de git
}


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------
def listar_escritorio(desktop: Path) -> tuple[list[Path], list[Path]]:
    """Separa el contenido del escritorio en carpetas y archivos."""
    if not desktop.is_dir():
        raise SystemExit(f"❌ No existe el escritorio: {desktop}")
    carpetas, archivos = [], []
    for elemento in sorted(desktop.iterdir()):
        (carpetas if elemento.is_dir() else archivos).append(elemento)
    return carpetas, archivos


def mostrar_listado(carpetas: list[Path], archivos: list[Path]) -> None:
    print(f"Carpetas: {len(carpetas)}")
    print("\n".join(str(c) for c in carpetas))
    print(f"\nArchivos: {len(archivos)}")
    print("\n".join(str(a) for a in archivos))
    print()


def comprimir_carpeta(carpeta: Path, zip_destino: Path) -> int:
    """Comprime la carpeta en zip_destino, salteando EXCLUIR y enlaces. Devuelve cuántos archivos agregó."""
    total = 0
    with zipfile.ZipFile(zip_destino, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zf:
        # os.walk permite "podar" carpetas: no entra a node_modules, venv, etc.
        for raiz, dirs, files in os.walk(carpeta):
            raiz = Path(raiz)
            dirs[:] = [d for d in dirs if d not in EXCLUIR and not (raiz / d).is_symlink()]
            for nombre in files:
                archivo = raiz / nombre
                if archivo.is_symlink():
                    continue
                zf.write(archivo, archivo.relative_to(carpeta.parent))
                total += 1
    return total


def backupear_carpeta(carpeta: Path, destino: Path, fecha: str) -> Path | None:
    """Crea el zip de una carpeta. Devuelve la ruta del zip, o None si se salteó o falló."""
    # Saltear enlaces simbólicos (ej: musica → /mnt/compartido, 19 GB)
    if carpeta.is_symlink():
        print(f"⏭️  Salteado (enlace): {carpeta.name}")
        return None

    zip_destino = destino / f"{carpeta.name}_{fecha}.zip"
    try:
        cantidad = comprimir_carpeta(carpeta, zip_destino)
    except (ValueError, OSError) as e:
        zip_destino.unlink(missing_ok=True)   # borra el zip a medio hacer
        print(f"❌ No se pudo comprimir {carpeta.name}: {e}")
        return None

    print(f"✅ Backup creado: {zip_destino} ({cantidad} archivos)")
    return zip_destino


def backupear_carpetas(carpetas: list[Path], destino: Path) -> list[Path]:
    """Crea un zip por carpeta, todos con la misma fecha. Devuelve los que se crearon bien."""
    destino.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d_%H%M")
    resultados = (backupear_carpeta(c, destino, fecha) for c in carpetas)
    return [z for z in resultados if z is not None]


def mostrar_resumen(backups: list[Path]) -> None:
    print(f"\nSe crearon {len(backups)} backups:")
    print("\n".join(str(z) for z in backups))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    carpetas, archivos = listar_escritorio(DESKTOP)
    mostrar_listado(carpetas, archivos)
    backups = backupear_carpetas(carpetas, DESTINO)
    mostrar_resumen(backups)


if __name__ == "__main__":
    main()