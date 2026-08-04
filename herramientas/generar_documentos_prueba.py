"""Genera documentos clínicos SINTÉTICOS para probar AnoniPRO.

Todos los datos son inventados (los DNI/NUSS se generan con dígitos de control
válidos para que la validación funcione, pero no pertenecen a nadie).

Uso:
    python herramientas/generar_documentos_prueba.py [carpeta_salida]

Genera:
    informe_alta.pdf        — informe de alta hospitalaria (PDF con texto)
    interconsulta.docx      — hoja de interconsulta (Word)
    analitica.pdf           — informe de laboratorio con membrete
"""

import sys
from pathlib import Path

import fitz
from docx import Document

SALIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "documentos_prueba"

# ── Datos sintéticos (DNI y NUSS con control válido, generados al azar) ────
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni_valido(numero: int) -> str:
    return f"{numero:08d}{LETRAS_DNI[numero % 23]}"


def nuss_valido(provincia: int, secuencial: int) -> str:
    base = int(f"{provincia:02d}{secuencial:08d}")
    return f"{provincia:02d} {secuencial:08d} {base % 97:02d}"


INFORME_ALTA = f"""INFORME DE ALTA HOSPITALARIA

Hospital Universitario Nuestra Señora de la Candelaria
Servicio de Pediatría — Unidad de Gastroenterología, Hepatología y Nutrición Pediátrica
Ctra. del Rosario 145, 38010 Santa Cruz de Tenerife. Tel: 922 60 20 00

Paciente: Laura Fernández Betancor
DNI: {dni_valido(43811223)}   NHC: 482913   Episodio: 2024-118332
F. Nac.: 14/02/2016 (8 años). Sexo: mujer
CIP: BBBBBBBBQX204871   NUSS: {nuss_valido(38, 44556677)}
Domicilio: Avda. de los Menceyes 27, 2ºA, 38320 La Laguna
Teléfono de contacto: 655 12 34 56 — laura.madre@correo.es

Fecha de ingreso: 12 de abril de 2024
Fecha de alta: 18/04/2024

Motivo de ingreso: dolor abdominal y vómitos de 48 horas de evolución.
Acude acompañada de su padre, D. Manuel Fernández Ruiz, y es valorada en
Urgencias del HUNSC.

Antecedentes: sin alergias medicamentosas conocidas. Vacunación al día.

Exploración: abdomen blando, doloroso en fosa ilíaca derecha.

Evolución: intervenida por el Servicio de Cirugía Pediátrica
(apendicectomía laparoscópica) sin incidencias. Afebril desde el segundo día.

Juicio clínico: apendicitis aguda flemonosa.

Tratamiento al alta: analgesia habitual. Control en su Centro de Salud de
Taco en 7 días. Cita de revisión el 3 de mayo de 2024 a las 10:30.

Fdo.: Dra. Carmen Delgado Hernández — Nº Col.: 38/38/07421
Pediatría, HUNSC. cdelgadoh@sescs.es
"""

INTERCONSULTA = f"""HOJA DE INTERCONSULTA

Complejo Hospitalario Universitario de Canarias (HUC)
Servicio solicitante: Medicina Interna. Servicio destino: Cardiología

Paciente: Antonio Medina Cabrera. Varón de 67 años.
DNI: {dni_valido(41902288)}  NHC: 91-448276  Tarjeta sanitaria: CIP 3800112299
Domicilio: Calle El Pilar 8, 38700 Santa Cruz de La Palma
Tfno.: 617 88 99 00

Fecha de solicitud: 21/03/2024. Preferente.

Motivo: paciente ingresado el 15/03/2024 por insuficiencia cardíaca
descompensada. Se solicita valoración de fibrilación auricular de reciente
diagnóstico. Ecocardiograma del 18 de marzo de 2024 con FEVI 38%.

Antecedentes: HTA, DM tipo 2, exfumador.

Firmado: Dr. José Ramón Afonso Pérez (Colegiado 38-38-11203)
Interconsulta revisada por la Dra. Nieves Toledo García, Cardiología HUC.
"""

ANALITICA = f"""LABORATORIO DE ANÁLISIS CLÍNICOS
Gerencia de Servicios Sanitarios del Área de Salud de La Palma
Hospital General de La Palma — Buenavista de Arriba s/n, 38713 Breña Alta
Teléfono: 922 18 50 00

Paciente: Rosario Concepción Díaz  (mujer, 54 años)
NHC: 204981  DNI: {dni_valido(42667211)}
Fecha de extracción: 02/05/2024 08:15
Médico peticionario: Dra. Pino Santana Vega — Atención Primaria, CS Los Llanos

RESULTADOS
Hemoglobina        13,2 g/dL     (12,0–16,0)
Leucocitos         6,4 x10³/µL   (4,0–11,0)
Glucosa            98 mg/dL      (70–110)
Creatinina         0,84 mg/dL    (0,50–1,10)
Colesterol total   201 mg/dL     (<200)
TSH                2,1 µUI/mL    (0,4–4,5)

Observaciones: sin hallazgos relevantes. Se remite copia al médico de familia.
Validado por: Dr. Andrés Lorenzo Brito, Facultativo de Análisis Clínicos.
"""


def crear_pdf(ruta: Path, texto: str):
    doc = fitz.open()
    pagina = doc.new_page()  # A4 por defecto
    rect = fitz.Rect(50, 50, 545, 792)
    pagina.insert_textbox(rect, texto, fontsize=10, fontname="helv")
    doc.save(str(ruta))
    doc.close()


def crear_docx(ruta: Path, texto: str):
    doc = Document()
    for linea in texto.split("\n"):
        doc.add_paragraph(linea)
    doc.save(str(ruta))


def crear_pdf_escaneado(ruta: Path, texto: str, dpi: int = 200):
    """PDF SIN capa de texto: se dibuja el texto, se rasteriza a imagen y se
    vuelve a insertar como imagen. Simula un documento escaneado para probar OCR."""
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_textbox(fitz.Rect(50, 50, 545, 792), texto, fontsize=11, fontname="helv")
    pix = pagina.get_pixmap(dpi=dpi)
    salida = fitz.open()
    p2 = salida.new_page(width=pagina.rect.width, height=pagina.rect.height)
    p2.insert_image(p2.rect, pixmap=pix)
    salida.save(str(ruta))
    doc.close()
    salida.close()


def crear_imagen(ruta: Path, texto: str, dpi: int = 200):
    """Imagen PNG con el texto (para probar el flujo de imágenes sueltas)."""
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_textbox(fitz.Rect(50, 50, 545, 792), texto, fontsize=11, fontname="helv")
    pagina.get_pixmap(dpi=dpi).save(str(ruta))
    doc.close()


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    crear_pdf(SALIDA / "informe_alta.pdf", INFORME_ALTA)
    crear_docx(SALIDA / "interconsulta.docx", INTERCONSULTA)
    crear_pdf(SALIDA / "analitica.pdf", ANALITICA)
    # Fase 2 — documentos para probar el OCR:
    crear_pdf_escaneado(SALIDA / "informe_alta_ESCANEADO.pdf", INFORME_ALTA)
    crear_imagen(SALIDA / "analitica_IMAGEN.png", ANALITICA)
    print(f"Documentos sintéticos creados en: {SALIDA}")
    print("  · informe_alta_ESCANEADO.pdf y analitica_IMAGEN.png sirven para probar el OCR (Fase 2)")
