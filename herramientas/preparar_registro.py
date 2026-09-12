"""Prepara los materiales para el Registro de la Propiedad Intelectual (programa
de ordenador). Genera en la carpeta `registro/`:

  - MEMORIA_TECNICA_ARAEMKA_Redact.docx  (memoria editable, con huecos para tus datos)
  - diagrama_flujo.png             (diagrama de flujo que se incrusta en la memoria)
  - CODIGO_FUENTE_ARAEMKA_Redact.pdf     (opcional con `--rpi`)
  - codigo-fuente/                 (los ficheros de código en bruto, copia limpia)

Solo incluye material propio del proyecto: excluye el entorno virtual, las
librerías de terceros, el visor PDF.js, los modelos y los empaquetados. Si se
han usado herramientas de IA, esa asistencia debe declararse con transparencia
al efectuar el depósito.
"""

import io
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from app.config import VERSION  # noqa: E402  (fuente única de versión)
SALIDA = RAIZ / "registro" / f"ARAEMKA-Redact-v{VERSION}"
ZIP_SAFE_CREATIVE = RAIZ / "registro" / f"ARAEMKA-Redact-v{VERSION}-Safe-Creative.zip"

# Ficheros de autoría propia (rutas relativas a la raíz del proyecto)
FICHEROS = [
    "backend/app/main.py",
    "backend/app/api.py",
    "backend/app/config.py",
    "backend/app/seguridad.py",
    "backend/app/almacen.py",
    "backend/app/textos.py",
    "backend/app/portable_main.py",  # se corrige abajo si está en backend/
    "backend/portable_main.py",
    "backend/app/detection/categorias.py",
    "backend/app/detection/validators.py",
    "backend/app/detection/reconocedores_es.py",
    "backend/app/detection/reconocedores_en.py",
    "backend/app/detection/idioma.py",
    "backend/app/detection/motor.py",
    "backend/app/detection/diagnostico_hardware.py",
    "backend/app/detection/capa3_llm.py",
    "backend/app/documentos/pdf_doc.py",
    "backend/app/documentos/docx_doc.py",
    "backend/app/documentos/xlsx_doc.py",
    "backend/app/documentos/ooxml.py",
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
    "backend/tests/test_universal.py",
    "backend/tests/test_ingles.py",
    "backend/tests/test_excel_metadatos_y_resaltado.py",
    "backend/tests/test_avisos_legales.py",
    "backend/tests/test_ocr_portable.py",
    "backend/tests/test_correcciones.py",
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
    "frontend/idiomas.js",
    "frontend/icono.svg",
    "herramientas/generar_documentos_prueba.py",
    "herramientas/evaluar_deteccion.py",
    "herramientas/preparar_registro.py",
    "herramientas/ficha_tecnica.py",
    "herramientas/generar_iconos.py",
    "herramientas/generar_version_windows.py",
    "herramientas/generar_avisos_terceros.py",
    "herramientas/probar_portable_windows.ps1",
    "herramientas/LEEME-WINDOWS.txt",
    "herramientas/construir_portable_mac.sh",
    "herramientas/construir_portable_windows.bat",
    "Dockerfile",
    "docker-compose.yml",
    "iniciar_mac.command",
    "README.md",
    "README.en.md",
    "AVISO-LEGAL.md",
    "LICENSE",
    "CODIGO-FUENTE.md",
    "THIRD-PARTY-NOTICES.md",
    "TRADEMARKS.md",
    "docs/INSTALAR-EN-NAS.md",
    "docs/PARA-DESARROLLADORES.md",
    "docs/PLAN-REGISTRO-MARCA-ARAEMKA.md",
    "web/index.html",
    ".github/workflows/construir-macos.yml",
    ".github/workflows/construir-windows.yml",
    ".github/workflows/publicar-sitio.yml",
    "AnoniPRO-synology/docker-compose.yml",
    "AnoniPRO-synology/INSTRUCCIONES.md",
]

TERCEROS = [
    ("FastAPI, Starlette, Uvicorn", "Framework y servidor web", "MIT / BSD-3"),
    ("Microsoft Presidio (presidio-analyzer)", "Orquestación de detección de PII (capa 1-2)", "MIT"),
    ("spaCy", "Motor de reconocimiento de entidades (capa 2)", "MIT"),
    ("Modelo es_core_news_md (spaCy)", "Modelo NER en español", "GPL-3.0"),
    ("Modelo en_core_web_md (spaCy)", "Modelo NER en inglés", "MIT"),
    ("PyMuPDF (fitz)", "Lectura y redacción destructiva de PDF", "AGPL-3.0 / comercial (Artifex)"),
    ("python-docx", "Lectura y escritura de documentos Word", "MIT"),
    ("openpyxl", "Lectura y escritura de libros Excel", "MIT"),
    ("pytesseract + Tesseract OCR", "OCR de escaneados e imágenes (capa Fase 2)", "Apache-2.0"),
    ("Pillow (PIL)", "Manejo de imágenes", "HPND (permisiva)"),
    ("itsdangerous", "Firma de la cookie de sesión", "BSD-3"),
    ("psutil", "Diagnóstico de hardware", "BSD-3"),
    ("PDF.js (Mozilla)", "Visor de PDF en el navegador (frontend/vendor)", "Apache-2.0"),
    ("Ollama y modelos LLM (Qwen3, Gemma 3)", "Capa 3 opcional; NO se distribuye con la app", "Apache-2.0 / licencias propias"),
]


def generar_diagrama(destino: Path):
    """Diagrama de flujo vertical sin depender de fuentes o librerías externas."""
    pasos = [
        "Documento de entrada\n(PDF, imagen, Word o Excel)",
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
    doc = fitz.open()
    pagina = doc.new_page(width=W, height=H)
    x0, x1 = 90, W - 90
    azul = (29 / 255, 93 / 255, 143 / 255)
    for i, texto in enumerate(pasos):
        y = margen_v + i * (alto_caja + gap)
        rgb = (234, 243, 251) if i not in (2, 3, 4) else (226, 240, 233)
        relleno = tuple(c / 255 for c in rgb)
        caja = fitz.Rect(x0, y, x1, y + alto_caja)
        pagina.draw_rect(caja, color=azul, fill=relleno, width=2)
        lineas = texto.split("\n")
        pagina.insert_textbox(
            fitz.Rect(x0 + 10, y + 15, x1 - 10, y + 43), lineas[0],
            fontsize=15, fontname="helv", color=(0.08, 0.08, 0.08),
            align=fitz.TEXT_ALIGN_CENTER,
        )
        if len(lineas) > 1:
            pagina.insert_textbox(
                fitz.Rect(x0 + 10, y + 49, x1 - 10, y + 76), lineas[1],
                fontsize=12, fontname="helv", color=(0.35, 0.35, 0.35),
                align=fitz.TEXT_ALIGN_CENTER,
            )
        if i < len(pasos) - 1:
            cx = (x0 + x1) / 2
            yf = y + alto_caja
            pagina.draw_line(fitz.Point(cx, yf), fitz.Point(cx, yf + gap), color=azul, width=2)
    pagina.insert_textbox(
        fitz.Rect(30, H - 28, W - 30, H - 8),
        "ARAEMKA Redact — Flujo de anonimización (todo el proceso ocurre en local)",
        fontsize=10, fontname="helv", color=(0.47, 0.47, 0.47),
        align=fitz.TEXT_ALIGN_CENTER,
    )
    pagina.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(destino)
    doc.close()


def generar_memoria(destino: Path, diagrama: Path, ficheros_info, incluye_pdf: bool = False):
    doc = Document()
    doc.core_properties.author = "José Ramón Alberto Alonso"
    doc.core_properties.last_modified_by = "José Ramón Alberto Alonso"
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
    r = sub2.add_run("Programa de ordenador: «ARAEMKA Redact»")
    r.bold = True; r.font.size = Pt(14)
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    h("1. Datos del autor y solicitante", 1)
    doc.add_paragraph("(Rellenar con sus datos antes de presentar la solicitud.)").italic = True
    campo("Nombre y apellidos", "José Ramón Alberto Alonso")
    campo("DNI / NIE")
    campo("Domicilio")
    campo("Correo electrónico y teléfono")
    campo("Condición", "Autor y titular de los derechos de explotación")

    h("2. Identificación de la obra", 1)
    campo("Título", "ARAEMKA Redact")
    campo("Tipo de obra", "Programa de ordenador")
    campo("Versión", VERSION)
    campo("Fecha de creación / finalización", "____ / ____ / 20____")
    campo("Naturaleza", "Obra original e independiente")

    h("3. Descripción del programa", 1)
    doc.add_paragraph(
        "ARAEMKA Redact es una aplicación para la anonimización de documentos clínicos que "
        "funciona de forma 100 % local: ningún dato del documento sale del equipo o de "
        "la red local, sin telemetría ni conexión a servicios externos. Está diseñada "
        "para uso sanitario, con interfaz en español, y detecta y elimina de forma "
        "irreversible los datos personales de informes clínicos (nombres de pacientes, "
        "familiares y personal sanitario, DNI/NIE, NUSS, CIP y tarjeta sanitaria —incluido "
        "el formato T.I.S. y los patrones de Canarias—, nº de historia clínica, teléfonos, "
        "direcciones, fechas, centros y servicios, entre otros).")
    doc.add_paragraph(
        "El programa admite documentos PDF con texto, PDF escaneados e imágenes (mediante "
        "reconocimiento óptico de caracteres), documentos Word y libros Excel `.xlsx`. La anonimización nunca se "
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
        "constancia. El depósito se refiere exclusivamente al material propio del proyecto "
        "relacionado en el apartado 9, incluida la selección, dirección, revisión e integración "
        "realizadas por el solicitante, y no a esos componentes de terceros.")
    tabla = doc.add_table(rows=1, cols=3)
    tabla.style = "Light Grid Accent 1"
    hc = tabla.rows[0].cells
    hc[0].text, hc[1].text, hc[2].text = "Componente", "Función", "Licencia"
    for comp, func, lic in TERCEROS:
        c = tabla.add_row().cells
        c[0].text, c[1].text, c[2].text = comp, func, lic
    doc.add_paragraph(
        "Nota: el titular ha autorizado la publicación de ARAEMKA Redact bajo AGPL-3.0-only, "
        "de forma compatible con PyMuPDF. La marca y el logotipo se tratan separadamente.").italic = True

    h("9. Listado de ficheros propios del proyecto", 1)
    ubicaciones = "la carpeta «codigo-fuente»"
    if incluye_pdf:
        ubicaciones = (
            "el documento «CODIGO_FUENTE_ARAEMKA_Redact.pdf» y la carpeta «codigo-fuente»"
        )
    doc.add_paragraph(
        f"El material depositado consta de {len(ficheros_info)} ficheros propios del proyecto, con un total "
        f"de {sum(n for _, n in ficheros_info)} líneas de código, cuyo contenido íntegro se "
        f"aporta en {ubicaciones}.")
    t2 = doc.add_table(rows=1, cols=2)
    t2.style = "Light List Accent 1"
    t2.rows[0].cells[0].text = "Fichero"
    t2.rows[0].cells[1].text = "Líneas"
    for ruta, n in ficheros_info:
        c = t2.add_row().cells
        c[0].text, c[1].text = ruta, str(n)

    h("10. Declaración de autoría y asistencia de IA", 1)
    doc.add_paragraph(
        "El solicitante declara que el programa ha sido desarrollado bajo su dirección y "
        "control, con asistencia de herramientas de inteligencia artificial. Ha seleccionado, "
        "revisado, corregido, integrado y validado el material relacionado en esta memoria. "
        "La declaración de titularidad se limita a las aportaciones humanas y derechos que "
        "legalmente le correspondan y no comprende componentes de terceros ni atribuye "
        "autoría humana a contenido que la legislación no considere protegible.")
    doc.add_paragraph()
    doc.add_paragraph("En ____________________, a ____ de ________________ de 20____.")
    doc.add_paragraph()
    doc.add_paragraph("Fdo.: ______________________________")

    doc.save(str(destino))


def generar_pdf_codigo(destino: Path, ficheros_existentes):
    """Un único PDF legible con todo el código, paginado y con nº de línea."""
    doc = fitz.open()
    ancho, alto = fitz.paper_size("a4")
    margen, tam = 40, 7.0
    fuente, max_cols, lineas_por_pagina = "cour", 112, 76

    # Portada
    pag = doc.new_page(width=ancho, height=alto)
    pag.insert_textbox(fitz.Rect(40, 120, ancho - 40, 400),
        "CÓDIGO FUENTE\n\nARAEMKA Redact\n\nPrograma de anonimización de documentos clínicos\n"
        f"Versión {VERSION}\n\n"
        f"{len(ficheros_existentes)} ficheros · {sum(n for _, n, _ in ficheros_existentes)} líneas\n\n"
        "Material propio del proyecto (excluye librerías de terceros)\n"
        "Documento aportado al Registro de la Propiedad Intelectual",
        fontsize=15, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)

    def nueva_pagina(ruta: str, continuacion: bool = False):
        p = doc.new_page(width=ancho, height=alto)
        etiqueta = f"{ruta} (continuación)" if continuacion else ruta
        p.draw_rect(
            fitz.Rect(margen - 4, margen - 2, ancho - margen + 4, margen + 16),
            fill=(0.11, 0.36, 0.56),
        )
        p.insert_text(
            (margen, margen + 11), etiqueta,
            fontsize=9, fontname="helv", color=(1, 1, 1),
        )
        return p

    for ruta, _, texto in ficheros_existentes:
        lineas_render = []
        for i, linea in enumerate(texto.splitlines(), 1):
            trozos = [linea[j:j + max_cols] for j in range(0, max(1, len(linea)), max_cols)] or [""]
            for k, trozo in enumerate(trozos):
                etiqueta = f"{i:4} " if k == 0 else "     "
                lineas_render.append(etiqueta + trozo)

        for inicio in range(0, len(lineas_render) or 1, lineas_por_pagina):
            pag = nueva_pagina(ruta, continuacion=inicio > 0)
            bloque = "\n".join(lineas_render[inicio:inicio + lineas_por_pagina])
            pag.insert_textbox(
                fitz.Rect(margen, margen + 25, ancho - margen, alto - margen),
                bloque, fontsize=tam, fontname=fuente,
                color=(0.15, 0.15, 0.15), lineheight=1.08,
            )
    doc.save(str(destino), garbage=4, deflate=True)
    doc.close()


def main():
    generar_pdf_rpi = "--rpi" in sys.argv[1:]
    # Cada versión vive en su propia carpeta. Nunca se borra el material histórico
    # de AnoniPRO ni depósitos anteriores, porque también acredita anterioridad.
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
    generar_memoria(
        SALIDA / "MEMORIA_TECNICA_ARAEMKA_Redact.docx",
        diagrama,
        info_docx,
        incluye_pdf=generar_pdf_rpi,
    )
    if generar_pdf_rpi:
        generar_pdf_codigo(SALIDA / "CODIGO_FUENTE_ARAEMKA_Redact.pdf", info_pdf)

    (SALIDA / "LEEME-SAFE-CREATIVE.txt").write_text(
        f"ARAEMKA Redact v{VERSION}\n"
        "Depósito de autoría de software y documentación.\n\n"
        "El paquete contiene únicamente una selección explícita de código y documentos "
        "propios. No contiene historiales clínicos, documentos de pacientes, credenciales, "
        "claves, entornos virtuales, modelos ni librerías de terceros.\n\n"
        "Declaración de creatividad recomendada: obra asistida por IA. El autor ha dirigido, "
        "seleccionado, revisado, corregido, integrado y validado el resultado.\n\n"
        "El depósito acredita contenido y fecha; no sustituye el registro oficial de la "
        "marca ARAEMKA ante la OEPM o la EUIPO.\n",
        encoding="utf-8",
    )

    manifestables = sorted(
        p for p in SALIDA.rglob("*")
        if p.is_file() and p.name != "MANIFEST.sha256"
    )
    lineas_manifest = []
    for fichero in manifestables:
        huella = hashlib.sha256(fichero.read_bytes()).hexdigest()
        lineas_manifest.append(f"{huella}  {fichero.relative_to(SALIDA).as_posix()}")
    (SALIDA / "MANIFEST.sha256").write_text(
        "\n".join(lineas_manifest) + "\n", encoding="ascii"
    )

    with zipfile.ZipFile(ZIP_SAFE_CREATIVE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fichero in sorted(p for p in SALIDA.rglob("*") if p.is_file()):
            zf.write(fichero, Path(SALIDA.name) / fichero.relative_to(SALIDA))

    print(f"Materiales generados en: {SALIDA}")
    print(f"  · {len(info_docx)} ficheros · {sum(n for _, n in info_docx)} líneas")
    nombres = ["MEMORIA_TECNICA_ARAEMKA_Redact.docx", "diagrama_flujo.png", "codigo-fuente/"]
    if generar_pdf_rpi:
        nombres.insert(1, "CODIGO_FUENTE_ARAEMKA_Redact.pdf")
    for nombre in nombres:
        print("  -", nombre)
    print(f"  - {ZIP_SAFE_CREATIVE.name}")


if __name__ == "__main__":
    main()
