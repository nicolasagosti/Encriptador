# Paso siguiente al compresor:  archivo.zip ──leer──► bytes ──guardar──► bites/
from pathlib import Path


def zips_a_bytes(rutas_zip, carpeta_salida):
    """Lee cada zip, guarda sus bytes en carpeta_salida y devuelve una lista con los bytes."""
    archivos_en_bytes = []
    for ruta_zip in rutas_zip:
        try:
            datos = ruta_zip.read_bytes()
            (carpeta_salida / ruta_zip.name).write_bytes(datos)   # mismo nombre, otra carpeta
            archivos_en_bytes.append(datos)
        except OSError as e:
            print(f"❌ No se pudo procesar {ruta_zip.name}: {e}")
    return archivos_en_bytes


destino = Path.home() / "backups"  / "backups_encriptados" # donde 01_Compresor.py deja los zips
bites = Path.home() / "backups"  / "bites"       # donde se guardan los bytes
bites.mkdir(parents=True, exist_ok=True)

backups_creados = sorted(destino.glob("*.zip"))

archivos_en_bytes = zips_a_bytes(backups_creados, bites)

print(f"Se guardaron {len(archivos_en_bytes)} de {len(backups_creados)} zips en {bites}")
print([len(datos) for datos in archivos_en_bytes])   # tamaño de cada uno
