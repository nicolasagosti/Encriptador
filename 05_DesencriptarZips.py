#!/usr/bin/env python3
"""
Desencripta los .zip de una carpeta que fueron encriptados con encriptar_zips.py (AES-256).

Por defecto genera zips normales (sin contraseña) en <carpeta>/desencriptados.
Con --extract, en vez de zips, extrae el contenido de cada uno en su propia subcarpeta.

Requisitos:
    pip install pyzipper

Uso:
    python desencriptar_zips.py /ruta/a/encriptados
    python desencriptar_zips.py /ruta/a/encriptados -r
    python desencriptar_zips.py /ruta/a/encriptados -o /ruta/salida
    python desencriptar_zips.py /ruta/a/encriptados --extract
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

try:
    import pyzipper
except ImportError:
    sys.exit("Falta la dependencia 'pyzipper'. Instalala con: pip install pyzipper")

CHUNK_SIZE = 1024 * 1024  # 1 MiB

log = logging.getLogger("desencriptar_zips")


def pedir_password() -> bytes:
    password = os.environ.get("ZIP_PASSWORD")
    if password:
        log.info("Usando contraseña de la variable de entorno ZIP_PASSWORD")
    else:
        password = getpass.getpass("Contraseña: ")
    return password.encode("utf-8")


def buscar_zips(carpeta: Path, recursivo: bool, excluir: Path) -> list[Path]:
    patron = carpeta.rglob("*") if recursivo else carpeta.glob("*")
    excluir = excluir.resolve()
    return sorted(
        ruta for ruta in patron
        if ruta.is_file()
        and ruta.suffix.lower() == ".zip"
        and excluir not in ruta.resolve().parents
    )


def ruta_segura(base: Path, nombre: str) -> Path:
    """Evita 'zip slip': que una entrada como '../../etc/passwd' escriba fuera de la carpeta destino."""
    destino = (base / nombre).resolve()
    if base.resolve() not in destino.parents and destino != base.resolve():
        raise ValueError(f"Entrada con ruta peligrosa: {nombre!r}")
    return destino


def desencriptar_a_zip(origen: Path, destino: Path, password: bytes) -> None:
    """Copia cada entrada del zip encriptado a un zip normal, sin contraseña."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".zip", dir=destino.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with pyzipper.AESZipFile(origen) as zin, zipfile.ZipFile(
            tmp, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            zin.setpassword(password)
            for info in zin.infolist():
                nueva = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                nueva.external_attr = info.external_attr
                nueva.compress_type = zipfile.ZIP_DEFLATED
                if info.is_dir():
                    zout.writestr(nueva, b"")
                    continue
                with zin.open(info) as src, zout.open(nueva, "w") as dst:
                    while chunk := src.read(CHUNK_SIZE):
                        dst.write(chunk)
        os.replace(tmp, destino)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def extraer(origen: Path, carpeta_destino: Path, password: bytes) -> None:
    """Extrae el contenido del zip encriptado en carpeta_destino."""
    with pyzipper.AESZipFile(origen) as zin:
        zin.setpassword(password)
        for info in zin.infolist():
            destino = ruta_segura(carpeta_destino, info.filename)
            if info.is_dir():
                destino.mkdir(parents=True, exist_ok=True)
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            with zin.open(info) as src, open(destino, "wb") as dst:
                while chunk := src.read(CHUNK_SIZE):
                    dst.write(chunk)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desencripta archivos .zip con contraseña (AES-256).")
    parser.add_argument("carpeta", type=Path, help="Carpeta que contiene los .zip encriptados")
    parser.add_argument("-r", "--recursive", action="store_true", help="Buscar zips también en subcarpetas")
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        help="Carpeta de salida (por defecto: <carpeta>/desencriptados)",
    )
    parser.add_argument(
        "-x", "--extract", action="store_true",
        help="Extraer el contenido en vez de generar zips sin contraseña",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Más detalle en la salida")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    carpeta: Path = args.carpeta.expanduser()
    if not carpeta.is_dir():
        log.error("No existe la carpeta: %s", carpeta)
        return 1
    output_dir = (args.output_dir or carpeta / "desencriptados").expanduser()

    validos = []
    for ruta in buscar_zips(carpeta, args.recursive, output_dir):
        if zipfile.is_zipfile(ruta):
            validos.append(ruta)
        else:
            log.warning("Se ignora, no es un zip válido: %s", ruta)
    if not validos:
        log.error("No se encontraron archivos .zip en %s", carpeta)
        return 1
    log.info("Se encontraron %d zip(s) en %s", len(validos), carpeta)

    password = pedir_password()

    errores = 0
    for origen in validos:
        relativo = origen.relative_to(carpeta)
        try:
            if args.extract:
                destino = output_dir / relativo.with_suffix("")  # una carpeta por zip
                extraer(origen, destino, password)
            else:
                destino = output_dir / relativo
                desencriptar_a_zip(origen, destino, password)
            log.info("OK   %s -> %s", origen, destino)
        except RuntimeError as exc:
            errores += 1
            if "password" in str(exc).lower():
                log.error("FAIL %s: contraseña incorrecta", origen)
            else:
                log.error("FAIL %s: %s", origen, exc)
        except Exception as exc:
            errores += 1
            log.error("FAIL %s: %s", origen, exc)

    log.info("Listo: %d desencriptados, %d con error.", len(validos) - errores, errores)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())