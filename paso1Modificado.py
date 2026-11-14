# ENCRIPTAR:  carpeta ──zip──► bytes ──cifrar con clave──► archivo.enc
#                                         ▲
#                         contraseña + salt ──KDF──► clave
#
# DESENCRIPTAR: archivo.enc ──► separar salt ──► misma clave ──► descifrar ──► unzip
import zipfile
from pathlib import Path
from datetime import datetime


def main():
    # 1. Rutas reales (Path.home() = /home/tu_usuario)
    desktop = Path.home() / "Desktop"   # /home/mechicush/Desktop
    #origen = desktop / "CarpetaAEncriptar"
    destino = Path.home() / "backups" / "DesktopAZip"   # /home/mechicush/backups/DesktopAZip
    carpetas = []
    archivos = []

    # Extensiones que ya vienen comprimidas: comprimirlas de nuevo no ahorra espacio
    YA_COMPRIMIDOS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mkv",
                      ".mp3", ".zip", ".gz", ".7z", ".rar", ".pdf", ".docx", ".xlsx"}

    ## Listar elementos en el escritorio
    for elemento in desktop.iterdir():
        # Saltear enlaces simbólicos (ej: musica → /mnt/compartido, 19 GB)
        if elemento.is_symlink():
            print(f"⏭️  Salteado (enlace): {elemento.name}")
            continue
        if elemento.is_dir():
            carpetas.append(elemento)
        elif elemento.is_file():
            archivos.append(elemento)

    print(f"Carpetas: {len(carpetas)}")
    print("\n".join([str(c) for c in carpetas]))
    print(f"\nArchivos: {len(archivos)}")
    print("\n".join([str(a) for a in archivos]))

    # 3. Crear la carpeta de destino si no existe
    destino.mkdir(parents=True, exist_ok=True)

    # 4. Nombre con fecha para no pisar backups anteriores (una sola fecha por corrida)
    fecha = datetime.now().strftime("%Y-%m-%d_%H%M")

    backups_creados = []   # rutas de los zips que se crearon bien

    # 5. Un zip por cada carpeta
    for elemento in carpetas:
        CarpetaZip = destino / f"{elemento.name}_{fecha}.zip"
        try:
            with zipfile.ZipFile(CarpetaZip, "w", zipfile.ZIP_DEFLATED,
                                 strict_timestamps=False) as zf:
                for archivo in elemento.rglob("*"):
                    if archivo.is_symlink():
                        continue   # no seguir enlaces dentro de la carpeta
                    if archivo.suffix.lower() in YA_COMPRIMIDOS:
                        tipo = zipfile.ZIP_STORED
                    else:
                        tipo = zipfile.ZIP_DEFLATED
                    zf.write(archivo, archivo.relative_to(elemento.parent),
                             compress_type=tipo)
            backups_creados.append(CarpetaZip)   # solo si no hubo error
            print(f"Backup creado: {CarpetaZip}")
        except (ValueError, OSError) as e:
            CarpetaZip.unlink(missing_ok=True)   # borra el zip a medio hacer
            print(f"❌ No se pudo comprimir {elemento.name}: {e}")

    # 6. Un único zip con todos los archivos sueltos del escritorio
    if archivos:
        ZipSueltos = destino / f"ArchivosSueltos_{fecha}.zip"
        try:
            with zipfile.ZipFile(ZipSueltos, "w", zipfile.ZIP_DEFLATED,
                                 strict_timestamps=False) as zf:
                for archivo in archivos:
                    if archivo.suffix.lower() in YA_COMPRIMIDOS:
                        tipo = zipfile.ZIP_STORED
                    else:
                        tipo = zipfile.ZIP_DEFLATED
                    zf.write(archivo, archivo.name, compress_type=tipo)
            backups_creados.append(ZipSueltos)
            print(f"Backup creado: {ZipSueltos}")
        except (ValueError, OSError) as e:
            ZipSueltos.unlink(missing_ok=True)
            print(f"❌ No se pudieron comprimir los archivos sueltos: {e}")

    # Resumen final (fuera del for)
    print(f"\nSe crearon {len(backups_creados)} backups:")
    print("\n".join(str(z) for z in backups_creados))

    # Devuelve las rutas para que el script que lo llama (ej: el de encriptar) las use
    return backups_creados


# Solo corre si ejecutás este archivo directo (python3 paso1Modificado.py),
# NO cuando lo importás desde otro script
if __name__ == "__main__":
    main()