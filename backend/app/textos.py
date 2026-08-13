"""Mensajes del servidor en español e inglés.

Los mensajes que ve el usuario (errores de subida, avisos del OCR…) se
traducen aquí. El idioma llega en la cabecera `X-Idioma` que envía la
interfaz; si no viene, se usa el `Accept-Language` del navegador y, en último
término, el español.
"""

MENSAJES: dict[str, dict[str, str]] = {
    "ocr_no_instalado": {
        "es": "Este documento necesita OCR (está escaneado o es una imagen) y "
              "Tesseract no está disponible en este equipo. En las versiones de "
              "Windows y NAS ya viene incluido; en macOS instálalo con "
              "«brew install tesseract tesseract-lang».",
        "en": "This document needs OCR (it is scanned or an image) and Tesseract is "
              "not available on this computer. The Windows and NAS versions already "
              "include it; on macOS install it with «brew install tesseract "
              "tesseract-lang».",
    },
    "login_bloqueado": {
        "es": "Demasiados intentos fallidos. Espera {espera} segundos e inténtalo de nuevo.",
        "en": "Too many failed attempts. Wait {espera} seconds and try again.",
    },
    "password_incorrecta": {
        "es": "Contraseña incorrecta.",
        "en": "Wrong password.",
    },
    "ia_fuera_de_red": {
        "es": "La dirección de la IA debe estar en tu red local (localhost o una IP "
              "privada). No se permiten servidores de internet: el texto del documento "
              "no debe salir de tu red.",
        "en": "The AI address must be on your local network (localhost or a private IP). "
              "Internet servers are not allowed: the document text must not leave your network.",
    },
    "ia_fuera_de_red_corto": {
        "es": "La dirección debe estar en tu red local (IP privada o localhost).",
        "en": "The address must be on your local network (private IP or localhost).",
    },
    "archivo_grande": {
        "es": "El archivo supera el máximo de {max_mb} MB.",
        "en": "The file is larger than the {max_mb} MB limit.",
    },
    "parametros_malos": {
        "es": "Parámetros de configuración con formato incorrecto.",
        "en": "The settings sent have an invalid format.",
    },
    "pdf_ilegible": {
        "es": "No se pudo leer el PDF: {error}",
        "en": "The PDF could not be read: {error}",
    },
    "imagen_ilegible": {
        "es": "No se pudo leer la imagen: {error}",
        "en": "The image could not be read: {error}",
    },
    "word_ilegible": {
        "es": "No se pudo leer el documento Word: {error}",
        "en": "The Word document could not be read: {error}",
    },
    "doc_antiguo": {
        "es": "Los .doc antiguos (Word 97-2003) no son compatibles. Ábrelo en Word y "
              "guárdalo como .docx.",
        "en": "Old .doc files (Word 97-2003) are not supported. Open it in Word and "
              "save it as .docx.",
    },
    "formato_no_compatible": {
        "es": "Formato no compatible: .{extension}. Usa PDF, Word (.docx) o una imagen "
              "(JPG, PNG, TIFF).",
        "en": "Unsupported format: .{extension}. Use PDF, Word (.docx) or an image "
              "(JPG, PNG, TIFF).",
    },
    "doc_caducado": {
        "es": "El documento ya no está en memoria (caducó o se eliminó). Vuelve a subirlo.",
        "en": "The document is no longer in memory (it expired or was deleted). Please upload it again.",
    },
    "nada_que_redactar": {
        "es": "No hay nada marcado para redactar.",
        "en": "Nothing is marked for redaction.",
    },
    "sin_resultado": {
        "es": "No hay resultado disponible. Aplica primero la redacción.",
        "en": "No result available. Apply the redaction first.",
    },
    "sin_auditoria": {
        "es": "No hay auditoría disponible. Aplica primero la redacción.",
        "en": "No audit report available. Apply the redaction first.",
    },
    "necesita_password": {
        "es": "Se necesita la contraseña de acceso.",
        "en": "The access password is required.",
    },
    # Avisos informativos que se muestran sobre el documento
    "ocr_escaneado": {
        "es": "PDF escaneado: se ha reconocido el texto por OCR en {n} página(s).",
        "en": "Scanned PDF: the text was recognised with OCR on {n} page(s).",
    },
    "ocr_paginas": {
        "es": "Algunas páginas ({n}) se han reconocido por OCR.",
        "en": "Some pages ({n}) were recognised with OCR.",
    },
    "ocr_imagen": {
        "es": "Imagen procesada con OCR. El documento anonimizado se entrega en PDF.",
        "en": "Image processed with OCR. The anonymised document is delivered as a PDF.",
    },
    "resto_posible": {
        "es": "«{texto}» podría seguir apareciendo en el documento final.",
        "en": "«{texto}» might still appear in the final document.",
    },
}


def idioma_de(request) -> str:
    """Idioma elegido en la interfaz (cabecera X-Idioma) o el del navegador."""
    elegido = (request.headers.get("X-Idioma") or "").lower()
    if elegido in ("es", "en"):
        return elegido
    acepta = (request.headers.get("Accept-Language") or "").lower()
    return "en" if acepta.startswith("en") else "es"


def t(clave: str, idioma: str = "es", **params) -> str:
    """Mensaje traducido, con los {parámetros} sustituidos."""
    entrada = MENSAJES.get(clave, {})
    texto = entrada.get(idioma) or entrada.get("es") or clave
    return texto.format(**params) if params else texto
