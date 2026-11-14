#!/usr/bin/env python3
"""
Encripta con contraseña (AES-256) todos los archivos .zip de una carpeta.
Funciona en Windows y en Linux (Kali).

Cada zip se reempaqueta en uno nuevo encriptado dentro de <carpeta>/encriptados
(o la carpeta indicada con -o), sin tocar el original salvo que se use --in-place.

La carpeta por defecto se configura en CARPETA_ZIPS_WINDOWS / CARPETA_ZIPS_LINUX.

Requisitos:
    pip install pyzipper

Uso:
    python encriptar_zips.py                                     # usa la carpeta por defecto
    python encriptar_zips.py /ruta/a/mis_zips
    python encriptar_zips.py /ruta/a/mis_zips -r                 # incluye subcarpetas
    python encriptar_zips.py /ruta/a/mis_zips -o /ruta/salida
    python encriptar_zips.py /ruta/a/mis_zips --in-place
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from rutas import obtener_desktop

try:
    import pyzipper
except ImportError:
    sys.exit("Falta la dependencia 'pyzipper'. Instalala con: pip install pyzipper")

# ---------------------------------------------------------------------------
# CONFIGURACIÓN: carpeta por defecto donde están los zips, según el sistema.
# Usá rutas absolutas. En Windows, siempre con r"..." (raw string).
# ---------------------------------------------------------------------------
CARPETA_ZIPS_WINDOWS = Path(r"C:\Users\Nicolas\zips")
CARPETA_ZIPS_LINUX = Path.home() / "backups"  / "DesktopAZip"

CARPETA_ZIPS = CARPETA_ZIPS_WINDOWS if sys.platform.startswith("win") else CARPETA_ZIPS_LINUX

MIN_PASSWORD_LENGTH = 8
CHUNK_SIZE = 1024 * 1024  # 1 MiB

log = logging.getLogger("encriptar_zips")

def buscar_zips(carpeta: Path, recursivo: bool, excluir: Path | None) -> list[Path]:
    """Devuelve los .zip de la carpeta (sin distinguir mayúsculas), ignorando la carpeta de salida."""
    patron = carpeta.rglob("*") if recursivo else carpeta.glob("*")
    excluir = excluir.resolve() if excluir else None
    encontrados = []
    for ruta in patron:
        if not ruta.is_file() or ruta.suffix.lower() != ".zip":
            continue
        if excluir and excluir in ruta.resolve().parents:
            continue  # no re-encriptar lo que ya generamos
        encontrados.append(ruta)
    return sorted(encontrados)


def ruta_destino(origen: Path, carpeta_base: Path, output_dir: Path | None) -> Path:
    if output_dir is None:  # --in-place
        return origen
    # Conserva la estructura de subcarpetas cuando se usa --recursive.
    return output_dir / origen.relative_to(carpeta_base)


def encriptar_zip(origen: Path, destino: Path, password: bytes) -> None:
    """Copia cada entrada del zip original a un zip nuevo encriptado con AES-256."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    # Se escribe en un archivo temporal en la misma carpeta y recién al final se
    # reemplaza el destino: si algo falla, no queda un zip corrupto a medias.
    fd, tmp_name = tempfile.mkstemp(suffix=".zip", dir=destino.parent)
    os.close(fd)
    tmp = Path(tmp_name)

    try:
        with zipfile.ZipFile(origen) as zin, pyzipper.AESZipFile(
            tmp,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zout:
            zout.setpassword(password)
            zout.setencryption(pyzipper.WZ_AES, nbits=256)

            for info in zin.infolist():
                if info.flag_bits & 0x1:
                    raise ValueError(f"'{origen.name}' ya tiene entradas encriptadas")

                # Hay que usar la clase de ZipInfo propia de AESZipFile.
                nueva = zout.zipinfo_cls(info.filename, date_time=info.date_time)
                nueva.external_attr = info.external_attr  # conserva permisos
                nueva.compress_type = pyzipper.ZIP_DEFLATED

                if info.is_dir():
                    zout.writestr(nueva, b"")
                    continue

                # Copia por streaming para no cargar archivos grandes en memoria.
                with zin.open(info) as src, zout.open(nueva, "w") as dst:
                    while chunk := src.read(CHUNK_SIZE):
                        dst.write(chunk)

        os.replace(tmp, destino)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def verificar(destino: Path, password: bytes) -> None:
    """Comprueba que el zip resultante se abre con la contraseña y no está corrupto."""
    with pyzipper.AESZipFile(destino) as z:
        z.setpassword(password)
        corrupto = z.testzip()
        if corrupto:
            raise ValueError(f"Verificación fallida en la entrada '{corrupto}'")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encripta archivos .zip con contraseña (AES-256).",
    )
    parser.add_argument(
        "carpeta", type=Path, nargs="?", default=CARPETA_ZIPS,
        help=f"Carpeta que contiene los archivos .zip (por defecto: {CARPETA_ZIPS})",
    )
    parser.add_argument("-r", "--recursive", action="store_true", help="Buscar zips también en subcarpetas")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "-o", "--output-dir", type=Path,
        help="Carpeta donde guardar los zips encriptados (por defecto: <carpeta>/encriptados)",
    )
    grupo.add_argument("--in-place", action="store_true", help="Reemplaza los zips originales")
    parser.add_argument("-v", "--verbose", action="store_true", help="Más detalle en la salida")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # En consolas viejas de Windows (cp1252/cp850) los acentos pueden romper el print.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    carpeta: Path = args.carpeta.expanduser()
    if not carpeta.is_dir():
        log.error("No existe la carpeta: %s", carpeta)
        return 1

    output_dir = None if args.in_place else (args.output_dir or carpeta / "encriptados").expanduser()

    # Validar todo antes de pedir la contraseña.
    validos: list[Path] = []
    for ruta in buscar_zips(carpeta, args.recursive, output_dir):
        if zipfile.is_zipfile(ruta):
            validos.append(ruta)
        else:
            log.warning("Se ignora, no es un zip válido: %s", ruta)

    if not validos:
        log.error("No se encontraron archivos .zip en %s", carpeta)
        return 1
    log.info("Se encontraron %d zip(s) en %s", len(validos), carpeta)

    password = "41103206Nn!!"

    errores = 0
    for origen in validos:
        destino = ruta_destino(origen, carpeta, output_dir)
        try:
            encriptar_zip(origen, destino, password)
            verificar(destino, password)
            log.info("OK   %s -> %s", origen, destino)
        except Exception as exc:  # seguimos con el resto aunque uno falle
            errores += 1
            log.error("FAIL %s: %s", origen, exc)

    log.info("Listo: %d encriptados, %d con error.", len(validos) - errores, errores)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())