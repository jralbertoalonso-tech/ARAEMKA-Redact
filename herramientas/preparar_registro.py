"""Prepara los materiales para el Registro de la Propiedad Intelectual (programa
de ordenador). Genera en la carpeta `registro/`:

  - MEMORIA_TECNICA_AnoniPRO.docx  (memoria editable, con huecos para tus datos)
  - diagrama_flujo.png             (diagrama de flujo que se incrusta en la memoria)
  - CODIGO_FUENTE_AnoniPRO.pdf     (todo TU código, legible, sin comprimir)
  - codigo-fuente/                 (los ficheros de código en bruto, copia limpia)

Solo incluye código de autoría propia: excluye el entorno virtual, las librerías
de terceros, el visor PDF.js, el modelo de lenguaje y los empaquetados.
"""

import io
import shutil
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "registro"
VERSION = "0.5.0"

# Ficheros de autoría propia (rutas relativas a la raíz del proyecto)
FICHEROS = [
    "backend/app/main.py",
    "backend/app/api.py",
    "backend/app/config.py",
    "backend/app/seguridad.py",
    "backend/app/almacen.py",
    "backend/app/portable_main.py",  # se corrige abajo si está en backend/
    "backend/portable_main.py",
    "backend/app/detection/categorias.py",
    "backend/app/detection/validators.py",
    "backend/app/detection/reconocedores_es.py",
    "backend/app/detection/motor.py",
    "backend/app/detection/diagnostico_hardware.py",
    "backend/app/detection/capa3_llm.py",
    "backend/app/documentos/pdf_doc.py",
    "backend/app/documentos/docx_doc.py",
    "backend/app/documentos/ocr.py",
    "backend/app/documentos/fechas.py",
    "backend/app/__init__.py",
    "backend/app/detection/__init__.py",
    "backend/app/documentos/__init__.py",
    "backend/requirements.txt",
    "backend/tests/test_mvp.py",
    "backend/tests/test_ocr.py",
    "backend/tests/test_capa3.py",
    "backend/tests/test_fase4.py",
    "backend/tests/test_fase5.py",
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
    "herramientas/generar_documentos_prueba.py",
    "herramientas/evaluar_deteccion.py",
    "herramientas/preparar_registro.py",
    "herramientas/construir_portable_mac.sh",
    "herramientas/construir_portable_windows.bat",
    "Dockerfile",
    "docker-compose.yml",
    "iniciar_mac.command",
    "README.md",
    "AnoniPRO-synology/docker-compose.yml",
    "AnoniPRO-synology/INSTRUCCIONES.md",
]

TERCEROS = [
    ("FastAPI, Starlette, Uvicorn", "Framework y servidor web", "MIT / BSD-3"),
    ("Microsoft Presidio (presidio-analyzer)", "Orquestación de detección de PII (capa 1-2)", "MIT"),
    ("spaCy", "Motor de reconocimiento de entidades (capa 2)", "MIT"),
    ("Modelo es_core_news_lg (spaCy)", "Modelo NER en español", "Verificar licencia del modelo"),
    ("PyMuPDF (fitz)", "Lectura y redacción destructiva de PDF", "AGPL-3.0 / comercial (Artifex)"),
    ("python-docx", "Lectura y escritura de documentos Word", "MIT"),
    ("pytesseract + Tesseract OCR", "OCR de escaneados e imágenes (capa Fase 2)", "Apache-2.0"),
    ("Pillow (PIL)", "Manejo de imágenes", "HPND (permisiva)"),
    ("itsdangerous", "Firma de la cookie de sesión", "BSD-3"),
    ("psutil", "Diagnóstico de hardware", "BSD-3"),
    ("PDF.js (Mozilla)", "Visor de PDF en el navegador (frontend/vendor)", "Apache-2.0"),
    ("Ollama y modelos LLM (Qwen3, Gemma 3)", "Capa 3 opcional; NO se distribuye con la app", "Apache-2.0 / licencias propias"),
]


def cargar_fuente(tam):
    for ruta in ["/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, tam)
            except Exception:
                pass
    return ImageFont.load_default()


def generar_diagrama(destino: Path):
    """Diagrama de flujo vertical del funcionamiento de AnoniPRO."""
    pasos = [
        "Documento de entrada\n(PDF, imagen o Word)",
        "Extracción de texto\n(directa u OCR con Tesseract si es escaneado)",
        "CAPA 1 — Reglas y validación\n(DNI, NUSS, CIP, T.I.S., teléfonos, fechas…)",
        "CAPA 2 — Modelo NER en español\n(nombres, lugares, organizaciones)",
        "CAPA 3 — LLM local (opcional)\n(menciones indirectas; Ollama/LM Studio)",
        "Verificación por el usuario\n(vista con resaltado; aceptar/descartar)",
        "Redacción DESTRUCTIVA\n(elimina texto o píxeles; o desplaza fechas / rango etario)",
        "Segunda pasada de verificación\n(re-escaneo del resultado)",
        "Descarga del documento anonimizado\n+ informe de auditoría",
    ]
    W, alto_caja, margen_v, gap = 900, 88, 40, 34
    H = margen_v * 2 + len(pasos) * alto_caja + (len(pasos) - 1) * gap
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    ftit = cargar_fuente(19)
    fsub = cargar_fuente(15)
    x0, x1 = 90, W - 90
    azul = (29, 93, 143)
    for i, texto in enumerate(pasos):
        y = margen_v + i * (alto_caja + gap)
        relleno = (234, 243, 251) if i not in (2, 3, 4) else (226, 240, 233)
        d.rounded_rectangle([x0, y, x1, y + alto_caja], radius=14, fill=relleno, outline=azul, width=2)
        lineas = texto.split("\n")
        d.text(((x0 + x1) / 2, y + 22), lineas[0], font=ftit, fill=(20, 20, 20), anchor="mm")
        if len(lineas) > 1:
            d.text(((x0 + x1) / 2, y + 56), lineas[1], font=fsub, fill=(90, 90, 90), anchor="mm")
        if i < len(pasos) - 1:
            cx = (x0 + x1) / 2
            yf = y + alto_caja
            d.line([cx, yf, cx, yf + gap], fill=azul, width=2)
            d.polygon([(cx - 7, yf + gap - 8), (cx + 7, yf + gap - 8), (cx, yf + gap)], fill=azul)
    d.text((W / 2, H - 14), "AnoniPRO — Flujo de anonimización (todo el proceso ocurre en local)",
           font=fsub, fill=(120, 120, 120), anchor="mm")
    img.save(destino)


def generar_memoria(destino: Path, diagrama: Path, ficheros_info):
    doc = Document()
    est = doc.styles["Normal"]
    est.font.name = "Calibri"
    est.font.size = Pt(11)

    def h(txt, nivel=1):
        p = doc.add_heading(txt, level=nivel)
        return p

    def campo(etq, valor="__________________________"):
        p = doc.add_paragraph()
        p.add_run(etq + ": ").bold = True
        p.add_run(valor)
        return p

    titulo = doc.add_heading("MEMORIA TÉCNICA", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("Solicitud de inscripción en el Registro de la Propiedad Intelectual")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub2 = doc.add_paragraph()
    r = sub2.add_run("Programa de ordenador: «AnoniPRO»")
    r.bold = True; r.font.size = Pt(14)
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    h("1. Datos del autor y solicitante", 1)
    doc.add_paragraph("(Rellenar con sus datos antes de presentar la solicitud.)").italic = True
    campo("Nombre y apellidos")
    campo("DNI / NIE")
    campo("Domicilio")
    campo("Correo electrónico y teléfono")
    campo("Condición", "Autor y titular de los derechos de explotación")

    h("2. Identificación de la obra", 1)
    campo("Título", "AnoniPRO")
    campo("Tipo de obra", "Programa de ordenador")
    campo("Versión", VERSION)
    campo("Fecha de creación / finalización", "____ / ____ / 20____")
    campo("Naturaleza", "Obra original e independiente")

    h("3. Descripción del programa", 1)
    doc.add_paragraph(
        "AnoniPRO es una aplicación para la anonimización de documentos clínicos que "
        "funciona de forma 100 % local: ningún dato del documento sale del equipo o de "
        "la red local, sin telemetría ni conexión a servicios externos. Está diseñada "
        "para uso sanitario, con interfaz en español, y detecta y elimina de forma "
        "irreversible los datos personales de informes clínicos (nombres de pacientes, "
        "familiares y personal sanitario, DNI/NIE, NUSS, CIP y tarjeta sanitaria —incluido "
        "el formato T.I.S. y los patrones de Canarias—, nº de historia clínica, teléfonos, "
        "direcciones, fechas, centros y servicios, entre otros).")
    doc.add_paragraph(
        "El programa admite documentos PDF con texto, PDF escaneados e imágenes (mediante "
        "reconocimiento óptico de caracteres) y documentos Word. La anonimización nunca se "
        "aplica a ciegas: el usuario revisa las detecciones resaltadas por colores, acepta o "
        "descarta cada una, y el programa realiza una segunda verificación del resultado. La "
        "redacción es destructiva real (elimina el texto de la capa de contenido o los píxeles "
        "de la imagen, y limpia los metadatos), de modo que el dato original no puede "
        "recuperarse. Además puede desplazar las fechas de forma consistente para preservar la "
        "cronología clínica, o sustituir la edad exacta por rangos etarios, y genera un informe "
        "de auditoría por documento sin incluir los datos redactados.")

    h("4. Lenguajes de programación", 1)
    doc.add_paragraph(
        "Python 3.12 (lógica de servidor y motor de detección), JavaScript (interfaz de "
        "usuario en el navegador), HTML y CSS (presentación), y scripts en Bash y Batch de "
        "Windows (arranque y empaquetado).")

    h("5. Entorno operativo", 1)
    doc.add_paragraph(
        "Aplicación web servida por un backend propio, accesible desde cualquier navegador. "
        "Se ejecuta en tres modalidades: (a) contenedor Docker sobre NAS Synology (DSM 7.x); "
        "(b) ejecutable portable para macOS y Windows 10/11, sin instalación ni permisos de "
        "administrador; (c) ejecución local para desarrollo. Requiere Python 3.10 o superior "
        "en las modalidades no empaquetadas. Funciona sin conexión a internet una vez instalado.")

    h("6. Arquitectura y funcionamiento", 1)
    doc.add_paragraph(
        "El motor de detección opera en tres capas complementarias: (1) reglas y expresiones "
        "regulares con validación de dígitos de control para identificadores españoles y "
        "canarios; (2) un modelo de reconocimiento de entidades en español ejecutable en CPU; "
        "y (3) opcionalmente, un modelo de lenguaje local (vía Ollama o LM Studio) para "
        "menciones indirectas. Los documentos se procesan en memoria y no se escriben en disco. "
        "El diagrama de flujo del proceso completo se muestra a continuación.")

    h("7. Diagrama de flujo", 1)
    doc.add_picture(str(diagrama), width=Inches(5.3))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    h("8. Componentes de terceros utilizados", 1)
    doc.add_paragraph(
        "El programa integra componentes de código abierto de terceros, cuya autoría "
        "corresponde a sus respectivos titulares y que se relacionan a continuación para "
        "constancia. La autoría objeto de esta inscripción se refiere EXCLUSIVAMENTE al "
        "código propio del solicitante (relacionado en el apartado 9), no a estos componentes.")
    tabla = doc.add_table(rows=1, cols=3)
    tabla.style = "Light Grid Accent 1"
    hc = tabla.rows[0].cells
    hc[0].text, hc[1].text, hc[2].text = "Componente", "Función", "Licencia"
    for comp, func, lic in TERCEROS:
        c = tabla.add_row().cells
        c[0].text, c[1].text, c[2].text = comp, func, lic
    doc.add_paragraph(
        "Nota: PyMuPDF se distribuye bajo licencia AGPL-3.0 (con opción de licencia comercial). "
        "Debe tenerse en cuenta esta condición para cualquier explotación futura del programa.").italic = True

    h("9. Listado de ficheros de código propio", 1)
    doc.add_paragraph(
        f"El programa consta de {len(ficheros_info)} ficheros de autoría propia, con un total "
        f"de {sum(n for _, n in ficheros_info)} líneas de código, cuyo contenido íntegro se "
        "aporta en el documento «CODIGO_FUENTE_AnoniPRO.pdf» y en la carpeta «codigo-fuente».")
    t2 = doc.add_table(rows=1, cols=2)
    t2.style = "Light List Accent 1"
    t2.rows[0].cells[0].text = "Fichero"
    t2.rows[0].cells[1].text = "Líneas"
    for ruta, n in ficheros_info:
        c = t2.add_row().cells
        c[0].text, c[1].text = ruta, str(n)

    h("10. Declaración de autoría", 1)
    doc.add_paragraph(
        "El solicitante declara ser el autor original del código propio relacionado en esta "
        "memoria, haberlo creado por sus propios medios y ostentar la titularidad de los "
        "derechos de explotación sobre el mismo.")
    doc.add_paragraph()
    doc.add_paragraph("En ____________________, a ____ de ________________ de 20____.")
    doc.add_paragraph()
    doc.add_paragraph("Fdo.: ______________________________")

    doc.save(str(destino))


def generar_pdf_codigo(destino: Path, ficheros_existentes):
    """Un único PDF legible con todo el código, paginado y con nº de línea."""
    doc = fitz.open()
    ancho, alto = fitz.paper_size("a4")
    margen, tam, salto = 40, 7.2, 9.2
    fuente, max_cols = "cour", 118

    # Portada
    pag = doc.new_page(width=ancho, height=alto)
    pag.insert_textbox(fitz.Rect(40, 120, ancho - 40, 400),
        "CÓDIGO FUENTE\n\nAnoniPRO\n\nPrograma de anonimización de documentos clínicos\n"
        f"Versión {VERSION}\n\n"
        f"{len(ficheros_existentes)} ficheros · {sum(n for _, n, _ in ficheros_existentes)} líneas\n\n"
        "Código de autoría propia (excluye librerías de terceros)\n"
        "Documento aportado al Registro de la Propiedad Intelectual",
        fontsize=15, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)

    def nueva_pagina():
        p = doc.new_page(width=ancho, height=alto)
        return p, margen

    for ruta, _, texto in ficheros_existentes:
        pag, y = nueva_pagina()
        # cabecera del fichero
        pag.draw_rect(fitz.Rect(margen - 4, y - 2, ancho - margen + 4, y + 16), fill=(0.11, 0.36, 0.56))
        pag.insert_text((margen, y + 11), ruta, fontsize=10, fontname="helv", color=(1, 1, 1))
        y += 26
        for i, linea in enumerate(texto.splitlines(), 1):
            # troceo de líneas largas
            trozos = [linea[j:j + max_cols] for j in range(0, max(1, len(linea)), max_cols)] or [""]
            for k, trozo in enumerate(trozos):
                if y > alto - margen:
                    pag, y = nueva_pagina()
                etiqueta = f"{i:4} " if k == 0 else "     "
                pag.insert_text((margen, y), etiqueta + trozo, fontsize=tam, fontname=fuente,
                                color=(0.15, 0.15, 0.15))
                y += salto
    doc.save(str(destino), garbage=4, deflate=True)
    doc.close()


def main():
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    (SALIDA / "codigo-fuente").mkdir(parents=True)

    # recopilar ficheros existentes (evitando duplicados y rutas erróneas)
    vistos, info_docx, info_pdf = set(), [], []
    for rel in FICHEROS:
        f = RAIZ / rel
        if not f.is_file() or rel in vistos:
            continue
        vistos.add(rel)
        texto = f.read_text(encoding="utf-8", errors="replace")
        n = len(texto.splitlines())
        info_docx.append((rel, n))
        info_pdf.append((rel, n, texto))
        # copia limpia
        destino_copia = SALIDA / "codigo-fuente" / rel
        destino_copia.parent.mkdir(parents=True, exist_ok=True)
        destino_copia.write_text(texto, encoding="utf-8")

    diagrama = SALIDA / "diagrama_flujo.png"
    generar_diagrama(diagrama)
    generar_memoria(SALIDA / "MEMORIA_TECNICA_AnoniPRO.docx", diagrama, info_docx)
    generar_pdf_codigo(SALIDA / "CODIGO_FUENTE_AnoniPRO.pdf", info_pdf)

    print(f"Materiales generados en: {SALIDA}")
    print(f"  · {len(info_docx)} ficheros · {sum(n for _, n in info_docx)} líneas")
    for nombre in ["MEMORIA_TECNICA_AnoniPRO.docx", "CODIGO_FUENTE_AnoniPRO.pdf",
                   "diagrama_flujo.png", "codigo-fuente/"]:
        print("  -", nombre)


if __name__ == "__main__":
    main()
