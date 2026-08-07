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


# ── Documentos de otros ámbitos (perfiles jurídico, empresa y facturas) ────

CONTRATO = f"""CONTRATO DE ARRENDAMIENTO DE VIVIENDA

Ante mí, Dña. Marta Ruiz Sanz, Notaria del Ilustre Colegio de Canarias.
Protocolo nº 1.245/2024.

COMPARECEN
De una parte, D. Antonio Medina Cabrera, mayor de edad, con DNI {dni_valido(41902288)},
pasaporte nº XDA123456, y domicilio en Calle El Pilar 8, 38700 Santa Cruz de La Palma.
Teléfono 617 88 99 00 y correo antonio.medina@correo.es

De otra, TALLERES PEREZ, S.L., con CIF A58818501, representada por
Dña. Nieves Toledo García, con DNI {dni_valido(42667211)}.

ESTIPULACIONES
Primera. Objeto: la vivienda sita en Avda. de los Menceyes 27, 2ºA, 38320 La Laguna,
con referencia catastral 9872023VH5797S0001WX, finca registral nº 45.678.

Segunda. Renta: 750 EUR mensuales, mediante transferencia a la cuenta
ES91 2100 0418 4502 0005 1332. Garantía con tarjeta 4539 5787 6362 1486.

Tercera. Se autoriza el estacionamiento del vehículo matrícula 1234 BCD.

Cuarta. Para cualquier controversia, las partes se someten al Juzgado de Primera
Instancia nº 3 de Santa Cruz de Tenerife. Procedimiento previo: autos 512/2024.

En Santa Cruz de Tenerife, a 12 de marzo de 2024.
"""

FACTURA = f"""FACTURA Nº F-2024-0451

GESTORIA MARTIN Y ASOCIADOS, S.L.
CIF B12345674 · Avda. de Anaga 45, 38001 Santa Cruz de Tenerife
Tel. 922 24 55 66 · admin@gestoriamartin.es

CLIENTE: Construcciones Delgado, S.A.
CIF A58818501
Domicilio: Calle El Pilar 8, 38700 Santa Cruz de La Palma
Persona de contacto: Nieves Toledo García - ntoledo@construcciones.es - 655 12 34 56

Fecha de emisión: 12/03/2024        Vencimiento: 12/04/2024
Nº de pedido: PED-2024-0912

Concepto: asesoría fiscal y laboral del primer trimestre
Base imponible: 1.200,00 EUR    IVA 21%: 252,00 EUR    TOTAL: 1.452,00 EUR

Forma de pago: transferencia a ES91 2100 0418 4502 0005 1332
Vehículo de reparto asociado: matrícula 4521 KLM
"""

NOMINA = f"""RECIBO DE SALARIOS - Mayo de 2026

Empresa: TALLERES PEREZ, S.L.   CIF A58818501
Centro de trabajo: Ctra. General del Norte 102, 38320 La Laguna

Trabajador: Yeray Santana Marrero
DNI: {dni_valido(43811223)}   NAF Seguridad Social: {nuss_valido(38, 44556677)}
Fecha de nacimiento: 14/02/1988   Antigüedad: 12/01/2019
Domicilio: C/ Herradores 45, 38201 La Laguna   Teléfono: 628 11 22 33
Correo: ysantana@correo.es   Nº de empleado: EMP-0457

Total devengado: 1.850,00 EUR   Deducciones: 315,00 EUR   Líquido: 1.535,00 EUR
Abono en cuenta: ES91 2100 0418 4502 0005 1332
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
    # Otros ámbitos (perfiles jurídico, empresa y facturación)
    crear_pdf(SALIDA / "contrato_JURIDICO.pdf", CONTRATO)
    crear_pdf(SALIDA / "factura_EMPRESA.pdf", FACTURA)
    crear_docx(SALIDA / "nomina_RRHH.docx", NOMINA)
    # Fase 2 — documentos para probar el OCR:
    crear_pdf_escaneado(SALIDA / "informe_alta_ESCANEADO.pdf", INFORME_ALTA)
    crear_imagen(SALIDA / "analitica_IMAGEN.png", ANALITICA)
    print(f"Documentos sintéticos creados en: {SALIDA}")
    print("  · informe_alta_ESCANEADO.pdf y analitica_IMAGEN.png sirven para probar el OCR")
    print("  · contrato_JURIDICO.pdf, factura_EMPRESA.pdf y nomina_RRHH.docx prueban los perfiles no clínicos")
