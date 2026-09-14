"""Contraseña simple opcional para el acceso web.

Si la variable de entorno ANONIPRO_PASSWORD está definida, todas las rutas de
la API (salvo /api/estado y /api/login) exigen una cookie de sesión firmada.
La clave de firma es efímera: al reiniciar el servidor las sesiones caducan.
"""

import hmac
import threading
import time

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, TimestampSigner

from .config import AJUSTES

NOMBRE_COOKIE = "anonipro_sesion"
DURACION_SESION_S = 12 * 3600  # 12 horas

# Límite de intentos de login: tras varios fallos, se bloquea la IP un rato para
# frenar la fuerza bruta contra la contraseña (que es simple) desde la red local.
_MAX_FALLOS = 5
_VENTANA_BLOQUEO_S = 60
_intentos: dict[str, list[float]] = {}
_intentos_lock = threading.Lock()

_firmador = TimestampSigner(AJUSTES.clave_firma)


def comprobar_password(password: str) -> bool:
    return hmac.compare_digest(password, AJUSTES.password)


def registrar_intento_login(ip: str, exito: bool) -> int:
    """Registra un intento de login. Devuelve los segundos que hay que esperar
    si la IP está bloqueada por exceso de fallos (0 si puede intentarlo)."""
    ahora = time.monotonic()
    with _intentos_lock:
        if exito:
            _intentos.pop(ip, None)
            return 0
        fallos = [t for t in _intentos.get(ip, []) if ahora - t < _VENTANA_BLOQUEO_S]
        if len(fallos) >= _MAX_FALLOS:
            return int(_VENTANA_BLOQUEO_S - (ahora - fallos[0])) + 1
        fallos.append(ahora)
        _intentos[ip] = fallos
        return 0


def crear_cookie_sesion(response: Response):
    valor = _firmador.sign(b"ok").decode()
    response.set_cookie(
        NOMBRE_COOKIE,
        valor,
        max_age=DURACION_SESION_S,
        httponly=True,
        samesite="strict",
        secure=AJUSTES.cookie_secure,
        path="/",
    )


def _sesion_valida(request: Request) -> bool:
    valor = request.cookies.get(NOMBRE_COOKIE, "")
    if not valor:
        return False
    try:
        _firmador.unsign(valor, max_age=DURACION_SESION_S)
        return True
    except BadSignature:
        return False


async def middleware_password(request: Request, call_next):
    """Bloquea la API si hay contraseña configurada y no hay sesión válida."""
    ruta = request.url.path
    if AJUSTES.requiere_password and ruta.startswith("/api"):
        request.state.autenticado = _sesion_valida(request)
        if ruta not in ("/api/login", "/api/estado") and not request.state.autenticado:
            from .textos import idioma_de, t
            return JSONResponse({"detail": t("necesita_password", idioma_de(request))},
                                status_code=401)
    else:
        request.state.autenticado = True
    return await call_next(request)
