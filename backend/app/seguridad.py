"""Contraseña simple opcional para el acceso web.

Si la variable de entorno ANONIPRO_PASSWORD está definida, todas las rutas de
la API (salvo /api/estado y /api/login) exigen una cookie de sesión firmada.
La clave de firma es efímera: al reiniciar el servidor las sesiones caducan.
"""

import hmac

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, TimestampSigner

from .config import AJUSTES

NOMBRE_COOKIE = "anonipro_sesion"
DURACION_SESION_S = 12 * 3600  # 12 horas

_firmador = TimestampSigner(AJUSTES.clave_firma)


def comprobar_password(password: str) -> bool:
    return hmac.compare_digest(password, AJUSTES.password)


def crear_cookie_sesion(response: Response):
    valor = _firmador.sign(b"ok").decode()
    response.set_cookie(
        NOMBRE_COOKIE, valor,
        max_age=DURACION_SESION_S, httponly=True, samesite="lax",
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
            return JSONResponse({"detail": "Se necesita la contraseña de acceso."}, status_code=401)
    else:
        request.state.autenticado = True
    return await call_next(request)
