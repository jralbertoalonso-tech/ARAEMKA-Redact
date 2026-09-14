"""Validación defensiva de destinos HTTP dentro de la red local.

La capa 3 puede enviar texto clínico todavía no anonimizado. Por eso no basta
con mirar la forma de la URL: se resuelve el nombre y se comprueba que *todas*
las direcciones obtenidas pertenecen a rangos locales explícitos.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse


_REDES_PERMITIDAS = tuple(
    ipaddress.ip_network(red)
    for red in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def _ip_local(ip: str) -> bool:
    try:
        direccion = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return False
    return any(direccion in red for red in _REDES_PERMITIDAS)


def url_en_red_privada(url: str, *, solo_base: bool = False) -> bool:
    """Comprueba esquema, credenciales, host y resolución de una URL local.

    ``solo_base`` restringe la ruta a la raíz o ``/v1`` para impedir que el
    valor configurado esconda rutas, consultas o fragmentos inesperados.
    """
    texto = (url or "").strip()
    if not texto:
        return False
    if "://" not in texto:
        texto = "http://" + texto
    try:
        partes = urllib.parse.urlsplit(texto)
        puerto = partes.port
    except (TypeError, ValueError):
        return False
    if partes.scheme not in ("http", "https"):
        return False
    if not partes.hostname or partes.username is not None or partes.password is not None:
        return False
    if partes.fragment or (solo_base and partes.query):
        return False
    if solo_base and partes.path.rstrip("/") not in ("", "/v1"):
        return False

    host = partes.hostname.rstrip(".").lower()
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
        direcciones = {host}
    except ValueError:
        # Solo se admiten nombres inequívocamente locales. Un dominio DNS normal
        # puede resolver hoy a una IP privada y mañana sufrir DNS rebinding.
        if host != "localhost" and not host.endswith(".local"):
            return False
        try:
            info = socket.getaddrinfo(host, puerto, type=socket.SOCK_STREAM)
        except OSError:
            return False
        direcciones = {entrada[4][0] for entrada in info if entrada[4]}

    return bool(direcciones) and all(_ip_local(ip) for ip in direcciones)


def exigir_peticion_privada(url: str) -> None:
    """Lanza ``ValueError`` si una petición HTTP podría salir de la red local."""
    if not url_en_red_privada(url):
        raise ValueError("El destino HTTP no pertenece a una red local permitida.")
