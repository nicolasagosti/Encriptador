"""Paso 1: hace un backup en .zip de cada carpeta del escritorio."""

import zipfile
from datetime import datetime
from pathlib import Path
from rutas import obtener_desktop

DESKTOP = Path.home() / "Desktop"
DESTINO = Path.home() / "backups" / "DesktopAZip"


def listar_contenido(directorio: Path) -> tuple[list[Path], list[Path]]:
    carpetas = [e for e in directorio.iterdir() if e.is_dir()]
    archivos = [e for e in directorio.iterdir() if not e.is_dir()]
    return carpetas, archivos


def comprimir_carpeta(carpeta: Path, destino: Path, fecha: str) -> Path:
    zip_path = destino / f"{carpeta.name}_{fecha}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                             strict_timestamps=False) as zf:
            for archivo in carpeta.rglob("*"):
                zf.write(archivo, archivo.relative_to(carpeta.parent))
    except (ValueError, OSError):
        zip_path.unlink(missing_ok=True)  # no dejar un zip a medias
        raise
    return zip_path


def main() -> list[Path]:
    desktop = obtener_desktop()

    carpetas, archivos = listar_contenido(desktop)
    print(f"Carpetas: {len(carpetas)}")
    print("\n".join(str(c) for c in carpetas))
    print(f"\nArchivos: {len(archivos)}")
    print("\n".join(str(a) for a in archivos))

    DESTINO.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d_%H%M")  # misma fecha para todo el backup

    backups_creados: list[Path] = []
    fallidos: list[str] = []

    for carpeta in carpetas:
        if carpeta.is_symlink():
            print(f"⏭️  Salteado (enlace): {carpeta.name}")
            continue
        try:
            zip_path = comprimir_carpeta(carpeta, DESTINO, fecha)
            backups_creados.append(zip_path)
            print(f"Backup creado: {zip_path}")
        except (ValueError, OSError) as e:
            fallidos.append(carpeta.name)
            print(f"❌ No se pudo comprimir {carpeta.name}: {e}")

    print(f"\nSe crearon {len(backups_creados)} backups:")
    print("\n".join(str(z) for z in backups_creados))

    if fallidos:
        # Cortamos la cadena: no se debe borrar nada sin backup
        raise RuntimeError(f"Fallaron los backups de: {', '.join(fallidos)}")

    return backups_creados


if __name__ == "__main__":
    main()