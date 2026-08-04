"""Almacén de documentos EN MEMORIA (nunca se escribe en disco).

Decisión de privacidad: los documentos subidos y sus versiones anonimizadas
viven solo en la RAM del proceso y se purgan automáticamente pasado un tiempo
de vida (TTL) configurable. Al parar el servidor no queda rastro en disco.
"""

import threading
import time
import uuid

from .config import AJUSTES


class SesionDocumento:
    """Estado de un documento subido durante su ciclo de vida."""

    def __init__(self, nombre: str, tipo: str, doc):
        self.id = uuid.uuid4().hex
        self.nombre = nombre                  # nombre original del archivo
        self.tipo = tipo                      # "pdf" | "docx"
        self.doc = doc                        # DocumentoPdf | DocumentoDocx
        self.creado_en = time.monotonic()
        self.detecciones: dict[str, dict] = {}   # id_detección → detección
        self.resultado: bytes | None = None      # archivo ya redactado
        self.avisos_verificacion: list[str] = []
        self.capa3_no_disponible = False         # capa 3 activada pero endpoint caído
        # Parámetros del último análisis (los reutiliza la segunda pasada)
        self.ultimo_analisis: dict = {"categorias": [], "lista_personalizada": [], "lista_blanca": []}
        self.auditoria: dict | None = None       # informe de auditoría (sin datos originales)
        self.delta_dias: int | None = None       # desplazamiento de fechas (consistente por documento)

    def tocar(self):
        """Renueva el TTL (se llama en cada acceso)."""
        self.creado_en = time.monotonic()

    @property
    def caducada(self) -> bool:
        return time.monotonic() - self.creado_en > AJUSTES.ttl_minutos * 60


class AlmacenMemoria:
    """Diccionario de sesiones con purga periódica en un hilo de fondo."""

    def __init__(self):
        self._sesiones: dict[str, SesionDocumento] = {}
        self._lock = threading.Lock()
        self._hilo = threading.Thread(target=self._purgar_periodicamente, daemon=True)
        self._hilo.start()

    def guardar(self, sesion: SesionDocumento):
        with self._lock:
            self._sesiones[sesion.id] = sesion

    def obtener(self, id_doc: str) -> SesionDocumento | None:
        with self._lock:
            sesion = self._sesiones.get(id_doc)
        if sesion is None or sesion.caducada:
            if sesion is not None:
                self.eliminar(id_doc)
            return None
        sesion.tocar()
        return sesion

    def eliminar(self, id_doc: str):
        with self._lock:
            self._sesiones.pop(id_doc, None)

    def _purgar_periodicamente(self):
        while True:
            time.sleep(60)
            with self._lock:
                caducadas = [i for i, s in self._sesiones.items() if s.caducada]
                for i in caducadas:
                    del self._sesiones[i]


ALMACEN = AlmacenMemoria()
