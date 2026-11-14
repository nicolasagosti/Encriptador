"""Obtiene la ruta real del escritorio en Windows y Linux."""

import subprocess
import sys
import uuid
from pathlib import Path

# GUID oficial de la carpeta "Escritorio" en Windows (FOLDERID_Desktop)
_FOLDERID_DESKTOP = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"


def _desktop_windows() -> Path:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

        def __init__(self, guid: str) -> None:
            super().__init__()
            u = uuid.UUID(guid)
            self.Data1, self.Data2, self.Data3 = u.fields[0], u.fields[1], u.fields[2]
            for i, b in enumerate(u.bytes[8:]):
                self.Data4[i] = b

    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32

    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.HRESULT  # lanza OSError si falla
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]

    ruta = ctypes.c_wchar_p()
    try:
        shell32.SHGetKnownFolderPath(ctypes.byref(GUID(_FOLDERID_DESKTOP)), 0, None,
                                     ctypes.byref(ruta))
        return Path(ruta.value)
    finally:
        ole32.CoTaskMemFree(ruta)  # Windows reserva la memoria; hay que liberarla


def _desktop_linux() -> Path:
    # xdg-user-dir respeta el idioma del sistema (Desktop, Escritorio, etc.)
    try:
        salida = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                text=True, check=True).stdout.strip()
        if salida and Path(salida) != Path.home():
            return Path(salida)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def obtener_desktop() -> Path:
    if sys.platform == "win32":
        ruta = _desktop_windows()
    else:
        ruta = _desktop_linux()

    if not ruta.is_dir():
        raise FileNotFoundError(f"No se encontró el escritorio en: {ruta}")
    return ruta


if __name__ == "__main__":
    print(obtener_desktop())