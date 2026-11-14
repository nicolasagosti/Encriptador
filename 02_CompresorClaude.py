import zipfile
from pathlib import Path
from datetime import datetime

desktop = Path.home() / "Desktop"
destino = Path.home() / "backups"
EXCLUIR = {"venv", ".venv", "__pycache__", "node_modules"}


def comprimir(origen, ruta_zip):
    """Comprime una carpeta o un archivo en ruta_zip."""
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED,
                         strict_timestamps=False) as zf:   # ← la clave
        if origen.is_file():
            zf.write(origen, origen.name)
            return
        for archivo in origen.rglob("*"):
            relativo = archivo.relative_to(origen.parent)   # CarpetaX/sub/archivo.txt
            if EXCLUIR.intersection(relativo.parts):        # saltea venv, __pycache__...
                continue
            zf.write(archivo, relativo)


destino.mkdir(parents=True, exist_ok=True)
fallidos = []

for elemento in desktop.iterdir():
    if elemento.name in EXCLUIR:
        continue

    fecha = datetime.now().strftime("%Y-%m-%d_%H%M")
    ruta_zip = destino / f"{elemento.name}_{fecha}.zip"     # acá SÍ va .zip

    try:
        comprimir(elemento, ruta_zip)
        print(f"✅ Backup creado: {ruta_zip}")
    except (ValueError, OSError) as e:
        ruta_zip.unlink(missing_ok=True)        # borra el zip incompleto
        fallidos.append(elemento.name)
        print(f"❌ No se pudo comprimir {elemento.name}: {e}")

if fallidos:
    print("\nFallaron:", ", ".join(fallidos))
else:
    print("\nTodo OK 🎉")
