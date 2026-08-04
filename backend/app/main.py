"""Punto de entrada de AnoniPRO.

Arranca el servidor web local que sirve la API y la interfaz. Ejecutar con:
    python -m app.main
o bien:
    uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

import logging
import sys
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import AJUSTES, VERSION
from .detection.motor import MOTOR
from .seguridad import middleware_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("anonipro")

# La carpeta del frontend está junto a `backend/` en el repositorio y en /app
# dentro del contenedor Docker. En el ejecutable portable (PyInstaller) los
# recursos se descomprimen en sys._MEIPASS.
if getattr(sys, "frozen", False):
    RUTA_FRONTEND = Path(getattr(sys, "_MEIPASS", ".")) / "frontend"
else:
    RUTA_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"

app = FastAPI(title="AnoniPRO", version=VERSION, docs_url=None, redoc_url=None)
app.middleware("http")(middleware_password)
app.include_router(router)
app.mount("/", StaticFiles(directory=str(RUTA_FRONTEND), html=True), name="frontend")


@app.on_event("startup")
def precargar_modelo():
    """Carga el modelo NER en segundo plano para que el primer documento no espere."""
    def _cargar():
        try:
            MOTOR._asegurar_cargado()
            log.info("Modelo NER listo: %s", MOTOR.modelo_cargado)
        except Exception as e:
            log.error("No se pudo cargar el modelo NER: %s", e)

    threading.Thread(target=_cargar, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=AJUSTES.puerto)
