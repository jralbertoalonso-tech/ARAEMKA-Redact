"""Configuración de la aplicación mediante variables de entorno.

Variables disponibles (todas opcionales):
  ANONIPRO_PASSWORD      Contraseña de acceso a la web. Vacía = sin contraseña.
  ANONIPRO_TTL_MINUTOS   Minutos que un documento permanece en memoria (defecto 30).
  ANONIPRO_MAX_MB        Tamaño máximo de archivo aceptado en MB (defecto 50).
  ANONIPRO_PUERTO        Puerto de escucha (defecto 8080).
"""

import os
import secrets
from dataclasses import dataclass, field


@dataclass
class Ajustes:
    password: str = os.environ.get("ANONIPRO_PASSWORD", "")
    ttl_minutos: int = int(os.environ.get("ANONIPRO_TTL_MINUTOS", "30"))
    max_mb: int = int(os.environ.get("ANONIPRO_MAX_MB", "50"))
    puerto: int = int(os.environ.get("ANONIPRO_PUERTO", "8080"))
    # Clave efímera para firmar la cookie de sesión (se regenera al reiniciar)
    clave_firma: str = field(default_factory=lambda: secrets.token_hex(32))

    @property
    def requiere_password(self) -> bool:
        return bool(self.password)


AJUSTES = Ajustes()

# Versión visible en el pie de la interfaz. Limpia y de cara al usuario; el
# detalle de cada versión vive en los mensajes de commit y en docs/.
VERSION = "0.9.2"
