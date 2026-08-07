"""Punto de entrada del MODO PORTABLE (ejecutable PyInstaller).

Arranca el servidor solo en este equipo (127.0.0.1, sin exponerse a la red) y
abre el navegador automáticamente. Sin instalación y sin permisos de
administrador: basta con descomprimir la carpeta y hacer doble clic.
"""

import socket
import sys
import threading
import time
import traceback
import webbrowser


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
    # Los imports pesados van DENTRO de main y bajo try: si falta algo en el
    # paquete, el usuario ve un mensaje claro en vez de una ventana que se cierra.
    import uvicorn

    from app.config import AJUSTES
    from app.main import app

    puerto = _puerto_libre(AJUSTES.puerto)
    url = f"http://127.0.0.1:{puerto}"
    print("──────────────────────────────────────────────")
    print("  AnoniPRO (modo portable)")
    print(f"  Abriendo {url} en tu navegador…")
    print("  Cierra esta ventana para parar la aplicación.")
    print("──────────────────────────────────────────────")

    def abrir_navegador():
        # Espera a que el servidor responda de verdad antes de abrir el
        # navegador (el modelo de idioma tarda; 2 s fijos no bastaban y se
        # abría una página de error).
        import urllib.error
        import urllib.request
        for _ in range(120):
            time.sleep(1.0)
            try:
                with urllib.request.urlopen(url + "/api/estado", timeout=2):
                    break
            except Exception:
                continue
        webbrowser.open(url)

    threading.Thread(target=abrir_navegador, daemon=True).start()
    # Solo escucha en 127.0.0.1: el modo portable es de uso personal, no servidor
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        # Sin esto, en Windows la consola se cierra al instante y el usuario no
        # llega a leer el error.
        print("\n──────────────────────────────────────────────")
        print("  ERROR: AnoniPRO no ha podido arrancar.")
        print("──────────────────────────────────────────────")
        traceback.print_exc()
        print("\nCopia este mensaje si necesitas ayuda para resolverlo.")
        try:
            input("\nPulsa Intro para cerrar esta ventana… ")
        except Exception:
            time.sleep(60)
        sys.exit(1)
