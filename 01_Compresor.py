# ENCRIPTAR:  carpeta ──zip──► bytes ──cifrar con clave──► archivo.enc
#                                         ▲
#                         contraseña + salt ──KDF──► clave
#
# DESENCRIPTAR: archivo.enc ──► separar salt ──► misma clave ──► descifrar ──► unzip
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# 1. Rutas reales (Path.home() = /home/tu_usuario)
desktop = Path.home() / "Desktop"   # /home/mechicush/Desktop
#origen = desktop / "CarpetaAEncriptar"
destino = Path.home() / "backups" / "DesktopAZip"   # /home/mechicush/backups/backups_encriptados
carpetas = []
archivos = []


## Listar elementos en el escritorio
for elemento in desktop.iterdir():
    if elemento.is_dir():
        carpetas.append(elemento)
    else: 
        
        archivos.append(elemento)

print(f"Carpetas: {len(carpetas)}")
print("\n".join([str(c) for c in carpetas])) 
print(f"\nArchivos: {len(archivos)}")
print("\n".join([str(c) for c in archivos])) 

# 3. Crear la carpeta de destino si no existe
destino.mkdir(parents=True, exist_ok=True)

backups_creados = []   # rutas de los zips que se crearon bien

for elemento in carpetas:
    # 2. Saltear enlaces simbólicos (ej: musica → /mnt/compartido, 19 GB)
    if elemento.is_symlink():
        print(f"⏭️  Salteado (enlace): {elemento.name}")
        continue

    # 4. Nombre con fecha para no pisar backups anteriores
    fecha = datetime.now().strftime("%Y-%m-%d_%H%M")
    CarpetaZip = destino / f"{elemento.name}_{fecha}.zip"   # ahora CON .zip
    try:
        with zipfile.ZipFile(CarpetaZip, "w", zipfile.ZIP_DEFLATED,
                             strict_timestamps=False) as zf:
            for archivo in elemento.rglob("*"):
                zf.write(archivo, archivo.relative_to(elemento.parent))
        backups_creados.append(CarpetaZip)   # solo si no hubo error
        print(f"Backup creado: {CarpetaZip}")
    except (ValueError, OSError) as e:
        CarpetaZip.unlink(missing_ok=True)   # borra el zip a medio hacer
        print(f"❌ No se pudo comprimir {elemento.name}: {e}")

# Resumen final (fuera del for)
print(f"\nSe crearon {len(backups_creados)} backups:")
print("\n".join(str(z) for z in backups_creados))


    
    
    
