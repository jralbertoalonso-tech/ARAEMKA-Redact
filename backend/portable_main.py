"""Punto de entrada del MODO PORTABLE (ejecutable PyInstaller).

Arranca el servidor solo en este equipo (127.0.0.1, sin exponerse a la red) y
abre el navegador automáticamente. Sin instalación y sin permisos de
administrador: basta con descomprimir la carpeta y hacer doble clic.
"""

import socket
import threading
import time
import webbrowser

import uvicorn

from app.config import AJUSTES
from app.main import app


def _puerto_libre(preferido: int) -> int:
    """Usa el puerto preferido si está libre; si no, pide uno al sistema."""
    try:
        with socket.socket() as s:
            s.bind(("127.0.0.1", preferido))
            return preferido
    except OSError:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def main():
    puerto = _puerto_libre(AJUSTES.puerto)
    url = f"http://127.0.0.1:{puerto}"
    print("──────────────────────────────────────────────")
    print("  AnoniPRO (modo portable)")
    print(f"  Abriendo {url} en tu navegador…")
    print("  Cierra esta ventana para parar la aplicación.")
    print("──────────────────────────────────────────────")

    def abrir_navegador():
        time.sleep(2.0)
        webbrowser.open(url)

    threading.Thread(target=abrir_navegador, daemon=True).start()
    # Solo escucha en 127.0.0.1: el modo portable es de uso personal, no servidor
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    main()
