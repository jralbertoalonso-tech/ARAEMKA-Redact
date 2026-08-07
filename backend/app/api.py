"""Rutas de la API REST.

Flujo normal desde el navegador:
  1. POST /api/documentos            → sube un archivo y devuelve las detecciones
  2. POST /api/documentos/{id}/analizar → re-analiza con otros interruptores/listas
  3. GET  /api/documentos/{id}/original → bytes del original (para la vista previa)
  4. POST /api/documentos/{id}/redactar → aplica la redacción destructiva
  5. GET  /api/documentos/{id}/resultado → descarga el documento anonimizado
"""

import hashlib
import io
import ipaddress
import json
import re
import time
import urllib.parse
from datetime import datetime

import fitz
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .almacen import ALMACEN, SesionDocumento
from .config import AJUSTES, VERSION
from .detection import capa3_llm as capa3
from .detection import categorias as cat
from .detection import diagnostico_hardware
from .detection.motor import MOTOR, resolver_solapamientos
from .documentos import fechas, ocr
from .documentos.docx_doc import CARACTER_REDACCION, DocumentoDocx
from .documentos.pdf_doc import DocumentoPdf, pdf_desde_imagen
from .seguridad import comprobar_password, crear_cookie_sesion, registrar_intento_login

router = APIRouter(prefix="/api")

# Tiempo máximo total que la capa 3 (LLM) puede consumir por documento.
CAPA3_PRESUPUESTO_S = 300


def _endpoint_en_red_privada(url: str) -> bool:
    """True solo si la URL apunta a la red local (localhost o RFC1918/mDNS).

    La capa 3 envía el texto clínico SIN anonimizar al endpoint configurado; hay
    que impedir que se apunte a un servidor de internet (exfiltración) o que se
    use el sondeo (`extra`) para escanear la red externa (SSRF).
    """
    try:
        host = urllib.parse.urlparse(url if "://" in url else "http://" + url).hostname
    except Exception:
        return False
    if not host:
        return False
    host = host.lower()
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # nombres que no son IP ni *.local: se rechazan
    return ip.is_private or ip.is_loopback or ip.is_link_local


def _asegurar_ocr_disponible():
    """Corta con un mensaje claro si se necesita OCR y Tesseract no está."""
    if not ocr.diagnostico()["disponible"]:
        raise HTTPException(
            422,
            "Este documento necesita OCR (está escaneado o es una imagen) y "
            "Tesseract no está instalado en este equipo. En la versión del NAS "
            "ya viene incluido; en macOS instálalo con «brew install tesseract "
            "tesseract-lang».",
        )


# ══════════════════════════════════════════════════════════════════════════
# Estado, login y catálogo de categorías
# ══════════════════════════════════════════════════════════════════════════

@router.get("/estado")
def estado(request: Request):
    diag_ocr = ocr.diagnostico()
    return {
        "version": VERSION,
        "modelo_ner": MOTOR.modelo_cargado or "(se carga con el primer documento)",
        "ocr_disponible": diag_ocr["disponible"],
        "ocr_espanol": diag_ocr["tiene_espanol"],
        "requiere_password": AJUSTES.requiere_password,
        "autenticado": getattr(request.state, "autenticado", not AJUSTES.requiere_password),
        "ttl_minutos": AJUSTES.ttl_minutos,
        "max_mb": AJUSTES.max_mb,
    }


class DatosLogin(BaseModel):
    password: str


@router.post("/login")
def login(datos: DatosLogin, request: Request, response: Response):
    if not AJUSTES.requiere_password:
        return {"ok": True}
    ip = request.client.host if request.client else "?"
    espera = registrar_intento_login(ip, exito=False)  # marca el intento
    if espera > 0:
        raise HTTPException(
            429, f"Demasiados intentos fallidos. Espera {espera} segundos e inténtalo de nuevo.")
    if not comprobar_password(datos.password):
        raise HTTPException(401, "Contraseña incorrecta.")
    registrar_intento_login(ip, exito=True)  # limpia el contador al acertar
    crear_cookie_sesion(response)
    return {"ok": True}


@router.get("/categorias")
def listar_categorias():
    return cat.como_dict()


# ══════════════════════════════════════════════════════════════════════════
# Capa 3 (LLM local opcional) y diagnóstico de hardware
# ══════════════════════════════════════════════════════════════════════════

@router.get("/diagnostico")
def diagnostico():
    """Hardware del equipo + recomendación concreta de qué usar para la capa 3."""
    hw = diagnostico_hardware.detectar()
    return {"hardware": hw, "recomendacion": diagnostico_hardware.recomendar(hw)}


@router.get("/capa3/estado")
def capa3_estado(extra: str = ""):
    """Configuración actual + endpoints LLM detectados en la red local."""
    # Solo se sondea `extra` si apunta a la red privada (evita SSRF).
    extra_seguro = extra if (extra and _endpoint_en_red_privada(extra)) else ""
    return {
        "config": capa3.CONFIG.como_dict(),
        "endpoints": capa3.detectar_endpoints(extra_seguro),
    }


class ConfigCapa3Body(BaseModel):
    activa: bool | None = None
    endpoint: str | None = None
    modelo: str | None = None
    timeout: int | None = None


@router.post("/capa3/configurar")
def capa3_configurar(body: ConfigCapa3Body):
    # El endpoint de la capa 3 recibe el texto clínico sin anonimizar: solo se
    # permite apuntar a la red local, nunca a un servidor de internet.
    if body.endpoint and not _endpoint_en_red_privada(body.endpoint):
        raise HTTPException(
            400, "La dirección de la IA debe estar en tu red local (localhost o una IP privada). "
                 "No se permiten servidores de internet: el texto clínico no debe salir de tu red.")
    capa3.CONFIG.actualizar(
        activa=body.activa, endpoint=body.endpoint, modelo=body.modelo, timeout=body.timeout
    )
    return {"config": capa3.CONFIG.como_dict()}


class ProbarCapa3Body(BaseModel):
    endpoint: str
    modelo: str


@router.post("/capa3/probar")
def capa3_probar(body: ProbarCapa3Body):
    """Prueba real: envía una petición mínima y comprueba que el modelo responde."""
    if not _endpoint_en_red_privada(body.endpoint):
        return {"ok": False, "error": "La dirección debe estar en tu red local (IP privada o localhost)."}
    return capa3.probar(body.endpoint, body.modelo)


# ══════════════════════════════════════════════════════════════════════════
# Subida y análisis
# ══════════════════════════════════════════════════════════════════════════

def _analizar_sesion(
    sesion: SesionDocumento,
    ids_categorias: list[str],
    lista_personalizada: list[str],
    lista_blanca: list[str],
) -> list[dict]:
    """Ejecuta la detección sobre todas las páginas/bloques y guarda el resultado."""
    detecciones: list[dict] = []
    contador = 0

    activas = set(ids_categorias)
    # Guarda los parámetros para reutilizarlos en la segunda pasada de verificación
    sesion.ultimo_analisis = {
        "categorias": list(ids_categorias),
        "lista_personalizada": list(lista_personalizada),
        "lista_blanca": list(lista_blanca),
    }
    # Capa 3: se comprueba UNA sola vez que el endpoint responde. Si está activada
    # pero no contesta, se salta en todo el documento (en vez de esperar el timeout
    # en cada página) y se avisa al usuario.
    usar_capa3 = capa3.CONFIG.lista_para_usar and capa3.comprobar_disponible()
    sesion.capa3_no_disponible = capa3.CONFIG.lista_para_usar and not usar_capa3
    # Presupuesto GLOBAL de tiempo para la capa 3 en todo el documento: evita que
    # un LLM lento cueste minutos por página en historias de 40 páginas.
    deadline = time.monotonic() + CAPA3_PRESUPUESTO_S if usar_capa3 else None

    def _revisar_llm(texto):
        return capa3.revisar_texto(texto, activas, deadline) if usar_capa3 else []

    if sesion.tipo == "pdf":
        for pagina in sesion.doc.paginas:
            base = MOTOR.detectar(pagina.texto, ids_categorias, lista_personalizada, lista_blanca)
            # Capa 3 (LLM local opcional): caza lo que las capas 1-2 no vieron
            extra = _revisar_llm(pagina.texto)
            for d in resolver_solapamientos(base + extra, pagina.texto):
                d["id"] = f"d{contador}"
                d["pagina"] = pagina.numero
                d["rects"] = [
                    [r.x0, r.y0, r.x1, r.y1]
                    for r in sesion.doc.rects_para_span(pagina.numero, d["inicio"], d["fin"])
                ]
                detecciones.append(d)
                contador += 1
        # Logos/membretes: detección estructural (imágenes), no del texto
        if "logo" in ids_categorias:
            for img in sesion.doc.imagenes_membrete():
                r = img["rect"]
                detecciones.append({
                    "id": f"d{contador}",
                    "pagina": img["pagina"],
                    "rects": [[r.x0, r.y0, r.x1, r.y1]],
                    "texto": f"Imagen de {img['zona']} (posible logo)",
                    "categoria": "logo",
                    "capa": 1,
                    "confianza": 0.6,
                    "contexto": f"Imagen situada en {'la cabecera' if img['zona'] == 'cabecera' else 'el pie'} de la página {img['pagina'] + 1}.",
                    "detector": "membrete",
                })
                contador += 1
    else:  # docx
        for bloque in sesion.doc.bloques:
            base = MOTOR.detectar(bloque.texto, ids_categorias, lista_personalizada, lista_blanca)
            extra = _revisar_llm(bloque.texto)
            for d in resolver_solapamientos(base + extra, bloque.texto):
                d["id"] = f"d{contador}"
                d["bloque"] = bloque.indice
                detecciones.append(d)
                contador += 1

    sesion.detecciones = {d["id"]: d for d in detecciones}
    return detecciones


@router.post("/documentos")
def subir_documento(
    archivo: UploadFile = File(...),
    categorias: str = Form("[]"),          # JSON: ["persona", "dni_nie", …]
    lista_personalizada: str = Form("[]"),  # JSON: términos a redactar siempre
    lista_blanca: str = Form("[]"),         # JSON: términos a respetar siempre
):
    # Endpoint SÍNCRONO (def): FastAPI lo ejecuta en el threadpool, de modo que
    # el trabajo pesado (OCR, NER, LLM) NO bloquea el event loop y otros usuarios
    # del NAS siguen siendo atendidos mientras se procesa un documento grande.
    contenido = archivo.file.read(AJUSTES.max_mb * 1024 * 1024 + 1)
    if len(contenido) > AJUSTES.max_mb * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera el máximo de {AJUSTES.max_mb} MB.")

    try:
        ids_cat_pre = json.loads(categorias)
        lista_pers = json.loads(lista_personalizada)
        lista_bl = json.loads(lista_blanca)
    except (ValueError, TypeError):
        raise HTTPException(422, "Parámetros de configuración con formato incorrecto.")

    nombre = archivo.filename or "documento"
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""

    aviso_ocr = None
    if extension == "pdf":
        try:
            doc = DocumentoPdf(contenido)
        except Exception as e:
            raise HTTPException(422, f"No se pudo leer el PDF: {e}")
        # PDF escaneado (sin capa de texto): aplicar OCR local en vez de rechazar
        if not doc.tiene_texto:
            paginas_ocr = doc.paginas_sin_texto()
            _asegurar_ocr_disponible()
            n = doc.aplicar_ocr(paginas_ocr)
            aviso_ocr = f"PDF escaneado: se ha reconocido el texto por OCR en {n} página(s)."
        else:
            # PDF mixto: OCR solo las páginas concretas que no tengan texto
            paginas_ocr = doc.paginas_sin_texto()
            if paginas_ocr and ocr.diagnostico()["disponible"]:
                doc.aplicar_ocr(paginas_ocr)
                aviso_ocr = f"Algunas páginas ({len(paginas_ocr)}) se han reconocido por OCR."
        sesion = SesionDocumento(nombre, "pdf", doc)
    elif extension in ("jpg", "jpeg", "png", "tif", "tiff", "bmp", "webp"):
        _asegurar_ocr_disponible()
        try:
            doc = DocumentoPdf(pdf_desde_imagen(contenido))
        except Exception as e:
            raise HTTPException(422, f"No se pudo leer la imagen: {e}")
        doc.aplicar_ocr()
        aviso_ocr = "Imagen procesada con OCR. El documento anonimizado se entrega en PDF."
        sesion = SesionDocumento(nombre, "pdf", doc)
    elif extension == "docx":
        try:
            doc = DocumentoDocx(contenido)
        except Exception as e:
            raise HTTPException(422, f"No se pudo leer el documento Word: {e}")
        sesion = SesionDocumento(nombre, "docx", doc)
    elif extension == "doc":
        raise HTTPException(
            422,
            "Los .doc antiguos (Word 97-2003) no son compatibles. "
            "Ábrelo en Word y guárdalo como .docx, o espera a la versión para "
            "el NAS, que los convertirá automáticamente.",
        )
    else:
        raise HTTPException(
            422,
            f"Formato no compatible: .{extension}. "
            "Usa PDF, Word (.docx) o una imagen (JPG, PNG, TIFF).",
        )

    ids_cat = ids_cat_pre or None
    detecciones = _analizar_sesion(
        sesion,
        ids_cat if ids_cat is not None else cat.IDS_POR_DEFECTO,
        lista_pers,
        lista_bl,
    )
    ALMACEN.guardar(sesion)

    respuesta = {
        "id": sesion.id,
        "nombre": sesion.nombre,
        "tipo": sesion.tipo,
        "detecciones": detecciones,
        "aviso_ocr": aviso_ocr,
        "por_ocr": any(getattr(p, "por_ocr", False) for p in getattr(doc, "paginas", [])),
        "capa3_no_disponible": sesion.capa3_no_disponible,
    }
    if sesion.tipo == "pdf":
        respuesta["paginas"] = [
            {"numero": p.numero, "ancho": p.ancho, "alto": p.alto} for p in doc.paginas
        ]
    else:
        respuesta["bloques"] = [
            {"indice": b.indice, "texto": b.texto, "origen": b.origen} for b in doc.bloques
        ]
    return respuesta


class PeticionAnalisis(BaseModel):
    categorias: list[str]
    lista_personalizada: list[str] = Field(default_factory=list)
    lista_blanca: list[str] = Field(default_factory=list)


@router.post("/documentos/{id_doc}/analizar")
def reanalizar(id_doc: str, peticion: PeticionAnalisis):
    sesion = ALMACEN.obtener(id_doc)
    if not sesion:
        raise HTTPException(404, "El documento ya no está en memoria (caducó o se eliminó). Vuelve a subirlo.")
    detecciones = _analizar_sesion(
        sesion, peticion.categorias, peticion.lista_personalizada, peticion.lista_blanca
    )
    return {"detecciones": detecciones, "capa3_no_disponible": sesion.capa3_no_disponible}


@router.get("/documentos/{id_doc}/original")
def descargar_original(id_doc: str):
    """Bytes del documento original, solo para la vista previa del navegador."""
    sesion = ALMACEN.obtener(id_doc)
    if not sesion:
        raise HTTPException(404, "El documento ya no está en memoria.")
    tipo_mime = "application/pdf" if sesion.tipo == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(content=sesion.doc.contenido, media_type=tipo_mime)


# ══════════════════════════════════════════════════════════════════════════
# Redacción y descarga
# ══════════════════════════════════════════════════════════════════════════

class ZonaManual(BaseModel):
    """Rectángulo dibujado a mano sobre la vista previa (solo PDF)."""
    pagina: int
    x0: float
    y0: float
    x1: float
    y1: float


class OpcionesRedaccion(BaseModel):
    """Alternativas a la redacción pura (Fase 5).

    fechas: "redactar" tacha las fechas de asistencia; "desplazar" las sustituye
            por fechas movidas un nº aleatorio de días IGUAL para todo el
            documento (se conserva la cronología clínica).
    edad:   "redactar" tacha la edad exacta; "rango" la sustituye por su banda
            quinquenal («47 años» → «45-49 años»). La FECHA de nacimiento se
            redacta siempre (es un identificador fuerte).
    """
    fechas: str = "redactar"   # "redactar" | "desplazar"
    edad: str = "redactar"     # "redactar" | "rango"


class PeticionRedaccion(BaseModel):
    aprobadas: list[str]                                  # ids de detecciones aceptadas
    zonas_manuales: list[ZonaManual] = Field(default_factory=list)
    textos_manuales: list[str] = Field(default_factory=list)  # términos añadidos a mano
    opciones: OpcionesRedaccion = Field(default_factory=OpcionesRedaccion)


def _spans_de_texto(texto: str, termino: str) -> list[tuple[int, int]]:
    """Todas las apariciones literales de `termino` (sin distinguir mayúsculas)."""
    if not termino.strip():
        return []
    return [m.span() for m in re.finditer(re.escape(termino.strip()), texto, re.IGNORECASE)]


def _delta_de_sesion(sesion: SesionDocumento) -> int:
    """Desplazamiento de días del documento: aleatorio, distinto de cero y
    CONSISTENTE (si se re-aplica la redacción, se usa el mismo)."""
    if getattr(sesion, "delta_dias", None) is None:
        import random
        sesion.delta_dias = random.choice([-1, 1]) * random.randint(30, 180)
    return sesion.delta_dias


def _texto_reemplazo(d: dict, opciones: OpcionesRedaccion, delta: int) -> str | None:
    """Texto de sustitución para una detección, o None si debe taparse en negro."""
    if d["categoria"] == "fecha" and opciones.fechas == "desplazar":
        return fechas.desplazar_fecha(d["texto"], delta)
    if d["categoria"] == "fecha_nacimiento" and opciones.edad == "rango" \
            and fechas.es_edad(d["texto"]):
        return fechas.rango_etario(d["texto"])
    return None


@router.post("/documentos/{id_doc}/redactar")
def redactar(id_doc: str, peticion: PeticionRedaccion):
    sesion = ALMACEN.obtener(id_doc)
    if not sesion:
        raise HTTPException(404, "El documento ya no está en memoria.")

    aprobadas = [sesion.detecciones[i] for i in peticion.aprobadas if i in sesion.detecciones]
    textos_redactados = [d["texto"] for d in aprobadas] + peticion.textos_manuales

    delta = _delta_de_sesion(sesion)

    if sesion.tipo == "pdf":
        zonas: list[tuple[int, fitz.Rect]] = []
        reemplazos: list[tuple[int, fitz.Rect, str]] = []
        for d in aprobadas:
            nuevo = _texto_reemplazo(d, peticion.opciones, delta)
            # La sustitución solo es viable si la detección ocupa un único
            # rectángulo (una línea); si no, se tapa en negro (conservador).
            if nuevo is not None and len(d["rects"]) == 1:
                x0, y0, x1, y1 = d["rects"][0]
                reemplazos.append((d["pagina"], fitz.Rect(x0, y0, x1, y1), nuevo))
                continue
            for x0, y0, x1, y1 in d["rects"]:
                zonas.append((d["pagina"], fitz.Rect(x0, y0, x1, y1)))
        for z in peticion.zonas_manuales:
            zonas.append((z.pagina, fitz.Rect(z.x0, z.y0, z.x1, z.y1)))
        # Términos añadidos a mano: buscar en todas las páginas
        for termino in peticion.textos_manuales:
            for pagina in sesion.doc.paginas:
                for ini, fin in _spans_de_texto(pagina.texto, termino):
                    for r in sesion.doc.rects_para_span(pagina.numero, ini, fin):
                        zonas.append((pagina.numero, r))
        if not zonas and not reemplazos:
            raise HTTPException(400, "No hay nada marcado para redactar.")
        resultado = sesion.doc.redactar(zonas, reemplazos)
    else:
        spans_por_bloque: dict[int, list[tuple]] = {}
        for d in aprobadas:
            nuevo = _texto_reemplazo(d, peticion.opciones, delta)
            span = (d["inicio"], d["fin"]) if nuevo is None else (d["inicio"], d["fin"], nuevo)
            spans_por_bloque.setdefault(d["bloque"], []).append(span)
        for termino in peticion.textos_manuales:
            for bloque in sesion.doc.bloques:
                for span in _spans_de_texto(bloque.texto, termino):
                    spans_por_bloque.setdefault(bloque.indice, []).append(span)
        if not spans_por_bloque:
            raise HTTPException(400, "No hay nada marcado para redactar.")
        resultado = sesion.doc.redactar(spans_por_bloque)

    # ── Segunda pasada de verificación (reforzada) ──────────────────────────
    # 1) Los textos aprobados NO deben seguir en el archivo (fuga crítica).
    # 2) Se re-escanea el resultado con el motor completo por si quedan otros
    #    posibles datos personales que nadie marcó (aviso informativo).
    rechazadas = {d["texto"].strip().lower()
                  for i, d in sesion.detecciones.items() if i not in set(peticion.aprobadas)}
    restos, residuales = _segunda_pasada(
        sesion, resultado, textos_redactados, rechazadas, peticion.opciones
    )

    sesion.resultado = resultado
    sesion.avisos_verificacion = [
        f"«{t}» podría seguir apareciendo en el documento final." for t in restos
    ]

    num_redacciones = len(aprobadas) + len(peticion.zonas_manuales) + len(peticion.textos_manuales)
    _generar_auditoria(sesion, aprobadas, peticion, num_redacciones, restos, residuales)

    return {
        "num_redacciones": num_redacciones,
        "avisos": sesion.avisos_verificacion,
        "residuales": residuales,
        "url_descarga": f"/api/documentos/{sesion.id}/resultado",
        "url_auditoria": f"/api/documentos/{sesion.id}/auditoria",
    }


def _segunda_pasada(
    sesion: SesionDocumento,
    resultado: bytes,
    textos_redactados: list[str],
    textos_rechazados: set[str],
    opciones: OpcionesRedaccion,
) -> tuple[list[str], list[dict]]:
    """Re-escanea el documento YA redactado.

    Devuelve (restos, residuales):
      - restos: textos aprobados que siguen presentes (no debería pasar nunca).
      - residuales: posibles datos personales detectados en el resultado que
        nadie marcó ni rechazó — el usuario decide si añadirlos y re-redactar.
    """
    if sesion.tipo == "pdf":
        doc_final = DocumentoPdf(resultado)
        # Escaneados/imágenes: el «texto» son píxeles → re-OCR del resultado
        if getattr(sesion.doc, "ocr_aplicado", False) and ocr.diagnostico()["disponible"]:
            doc_final.aplicar_ocr()
        textos_finales = [p.texto for p in doc_final.paginas]
    else:
        doc_final = DocumentoDocx(resultado)
        textos_finales = [b.texto for b in doc_final.bloques]

    todo = " ".join(textos_finales).lower()
    restos = [t for t in textos_redactados if t.strip() and t.strip().lower() in todo]

    # Re-detección completa con la misma configuración del último análisis
    params = sesion.ultimo_analisis
    vistos: set[str] = set()
    residuales: list[dict] = []
    for texto in textos_finales:
        if not texto.strip():
            continue
        for d in MOTOR.detectar(
            texto, params["categorias"], params["lista_personalizada"], params["lista_blanca"]
        ):
            clave = d["texto"].strip().lower()
            if not clave or clave in vistos or clave in textos_rechazados:
                continue
            if d["categoria"] == "logo" or CARACTER_REDACCION in d["texto"]:
                continue
            if _es_fragmento_huerfano(d["texto"]):
                continue
            # Las fechas desplazadas y los rangos etarios son sustituciones
            # INTENCIONADAS: no deben aparecer como residuales.
            if d["categoria"] == "fecha" and opciones.fechas == "desplazar":
                continue
            if d["categoria"] == "fecha_nacimiento" and opciones.edad == "rango" \
                    and fechas.es_edad(d["texto"]):
                continue
            vistos.add(clave)
            residuales.append({"texto": d["texto"], "categoria": d["categoria"]})
    return restos, residuales[:30]  # tope defensivo para la respuesta


# Palabras sueltas que quedan «huérfanas» junto a una zona redactada y que el
# motor puede confundir con entidades al re-escanear (no son datos personales).
_TOKENS_HUERFANOS = {
    "de", "del", "la", "las", "los", "el", "y", "e", "en", "a", "con", "por",
    "fdo", "fdo.", "dr", "dra", "dr.", "dra.", "nº", "no", "col", "col.",
    "nº col", "tel", "tfno", "cip", "nhc", "dni", "nuss", "correo", "paciente",
}


def _es_fragmento_huerfano(texto: str) -> bool:
    """True si el «residual» es solo un resto de plantilla sin valor identificativo."""
    limpio = texto.strip().strip(".:;,–—-ºª()")
    if len(limpio) < 4:
        return True
    tokens = [t.strip(".:;,–—-ºª()").lower() for t in limpio.split()]
    return all(t in _TOKENS_HUERFANOS or len(t) <= 1 for t in tokens)


def _generar_auditoria(sesion, aprobadas, peticion, num_redacciones, restos, residuales):
    """Crea el informe de auditoría. NUNCA incluye los datos redactados."""
    por_categoria: dict[str, dict] = {}
    ids_aprobadas = set(peticion.aprobadas)
    for i, d in sesion.detecciones.items():
        c = por_categoria.setdefault(d["categoria"], {"detectadas": 0, "redactadas": 0})
        c["detectadas"] += 1
        if i in ids_aprobadas:
            c["redactadas"] += 1

    params = sesion.ultimo_analisis
    sesion.auditoria = {
        "aplicacion": f"AnoniPRO {VERSION}",
        "fecha_hora": datetime.now().isoformat(timespec="seconds"),
        "documento": sesion.nombre,
        "tipo": sesion.tipo,
        "extension_salida": "pdf" if sesion.tipo == "pdf" else "docx",
        "ocr_aplicado": bool(getattr(sesion.doc, "ocr_aplicado", False)),
        "motor": {
            "modelo_ner": MOTOR.modelo_cargado,
            "capa3_activa": capa3.CONFIG.activa,
            "capa3_modelo": capa3.CONFIG.modelo if capa3.CONFIG.activa else None,
        },
        "configuracion": {
            "categorias_activas": params["categorias"],
            "terminos_personalizados": len(params["lista_personalizada"]),
            "terminos_lista_blanca": len(params["lista_blanca"]),
        },
        "redaccion": {
            "total_aplicada": num_redacciones,
            "detecciones_aprobadas": len(aprobadas),
            "detecciones_rechazadas": len(sesion.detecciones) - len(aprobadas),
            "zonas_manuales": len(peticion.zonas_manuales),
            "textos_manuales": len(peticion.textos_manuales),
            "por_categoria": por_categoria,
            # El VALOR del desplazamiento no se registra a propósito:
            # conocerlo permitiría reconstruir las fechas reales.
            "modo_fechas": "desplazadas" if peticion.opciones.fechas == "desplazar" else "redactadas",
            "modo_edad": "rango_etario" if peticion.opciones.edad == "rango" else "redactada",
        },
        "verificacion_segunda_pasada": {
            "textos_aprobados_restantes": len(restos),
            "posibles_datos_residuales": len(residuales),
            "residuales_por_categoria": _cuenta_por_categoria(residuales),
        },
        "sha256_resultado": hashlib.sha256(sesion.resultado or b"").hexdigest(),
        "nota": (
            "Este informe registra QUÉ se redactó y con qué configuración, "
            "sin incluir ninguno de los datos originales redactados."
        ),
    }


def _cuenta_por_categoria(residuales: list[dict]) -> dict[str, int]:
    cuenta: dict[str, int] = {}
    for r in residuales:
        cuenta[r["categoria"]] = cuenta.get(r["categoria"], 0) + 1
    return cuenta


@router.get("/documentos/{id_doc}/auditoria")
def descargar_auditoria(id_doc: str):
    """Informe de auditoría en JSON (sin datos originales), para guardar localmente."""
    sesion = ALMACEN.obtener(id_doc)
    if not sesion or sesion.auditoria is None:
        raise HTTPException(404, "No hay auditoría disponible. Aplica primero la redacción.")
    base = sesion.nombre.rsplit(".", 1)[0]
    contenido = json.dumps(sesion.auditoria, ensure_ascii=False, indent=2)
    return Response(
        content=contenido,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{base}_auditoria.json"'},
    )


@router.get("/documentos/{id_doc}/resultado")
def descargar_resultado(id_doc: str):
    sesion = ALMACEN.obtener(id_doc)
    if not sesion or sesion.resultado is None:
        raise HTTPException(404, "No hay resultado disponible. Aplica primero la redacción.")
    base = sesion.nombre.rsplit(".", 1)[0]
    extension = "pdf" if sesion.tipo == "pdf" else "docx"
    tipo_mime = "application/pdf" if sesion.tipo == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return StreamingResponse(
        io.BytesIO(sesion.resultado),
        media_type=tipo_mime,
        headers={
            "Content-Disposition": f'attachment; filename="{base}_anonimizado.{extension}"'
        },
    )


@router.delete("/documentos/{id_doc}")
def eliminar_documento(id_doc: str):
    """Borra el documento de la memoria inmediatamente (botón «Terminar»)."""
    ALMACEN.eliminar(id_doc)
    return {"ok": True}
