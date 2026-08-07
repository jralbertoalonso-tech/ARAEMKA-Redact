"""Catálogo de datos personales que la aplicación detecta.

AnoniPRO es de uso general: sirve para documentos clínicos, jurídicos,
laborales, facturas y papeles personales. Cada categoría tiene un identificador
estable (se usa en la API y en los perfiles), su nombre visible en español e
inglés, un grupo (para el panel de interruptores) y un color (para el resaltado).

Los identificadores (`id`, `grupo`) NUNCA se traducen: son la clave técnica.
"""

from dataclasses import dataclass

# Grupos del panel, en el orden en que se muestran: (id, nombre ES, nombre EN)
GRUPOS = [
    ("identidad", "Personas e identidad", "People and identity"),
    ("contacto", "Contacto y ubicación", "Contact and location"),
    ("economico", "Datos bancarios y fiscales", "Banking and tax data"),
    ("salud", "Datos de salud", "Health data"),
    ("tramites", "Expedientes, bienes y vehículos", "Case files, property and vehicles"),
    ("organizaciones", "Organizaciones", "Organisations"),
    ("otros", "Otros", "Other"),
]


@dataclass(frozen=True)
class Categoria:
    id: str              # identificador estable usado por la API
    nombre: str          # nombre visible (español)
    grupo: str           # grupo del panel (ver GRUPOS)
    color: str           # color de resaltado en la vista de verificación
    descripcion: str     # texto de ayuda del interruptor (español)
    nombre_en: str = ""      # nombre visible (inglés)
    descripcion_en: str = ""  # texto de ayuda (inglés)
    activa_por_defecto: bool = True


CATEGORIAS: list[Categoria] = [
    # ── Personas e identidad ──────────────────────────────────────────────
    Categoria("persona", "Nombres de personas", "identidad", "#e5484d",
              "Nombres y apellidos de cualquier persona: interesados, clientes, "
              "familiares, empleados…",
              "People's names",
              "First names and surnames of anyone: parties, clients, relatives, staff…"),
    Categoria("dni_nie", "DNI / NIE", "identidad", "#d6409f",
              "Documento nacional de identidad o NIE, con letra de control verificada.",
              "National ID (DNI / NIE)",
              "Spanish national identity or foreigner number, with its check letter verified."),
    Categoria("pasaporte", "Pasaporte", "identidad", "#ab4aba",
              "Números de pasaporte (formato español), detectados por contexto.",
              "Passport",
              "Passport numbers, detected from their label."),
    Categoria("fecha_nacimiento", "Fecha de nacimiento y edad", "identidad", "#8e4ec6",
              "Fechas junto a «nacimiento/nacido» y edades exactas («47 años»).",
              "Date of birth and age",
              "Dates next to «born/date of birth» and exact ages («47 years»)."),
    Categoria("sexo", "Sexo", "identidad", "#6e56cf",
              "Menciones explícitas de sexo (varón/mujer/hombre). Al arrancar está "
              "activo, como todo lo demás; los perfiles concretos lo desactivan "
              "porque por sí solo rara vez identifica a nadie.",
              "Sex",
              "Explicit mentions of sex (male/female). On by default like everything "
              "else; the specific profiles switch it off because on its own it rarely "
              "identifies anyone."),

    # ── Contacto y ubicación ──────────────────────────────────────────────
    Categoria("direccion", "Direcciones postales", "contacto", "#3e63dd",
              "Calles, avenidas y domicilios detectados por patrón o por el modelo de lenguaje.",
              "Postal addresses",
              "Streets and home addresses, detected by pattern or by the language model."),
    Categoria("telefono", "Teléfonos", "contacto", "#0090ff",
              "Teléfonos españoles (móviles y fijos), con prefijo y longitud validados.",
              "Phone numbers",
              "Spanish landline and mobile numbers, with prefix and length validated."),
    Categoria("email", "Correos electrónicos", "contacto", "#00a2c7",
              "Direcciones de correo electrónico.",
              "E-mail addresses",
              "E-mail addresses."),
    Categoria("localidad", "Localidades y códigos postales", "contacto", "#7d9bf5",
              "Nombres de lugar y códigos postales españoles.",
              "Towns and postcodes",
              "Place names and Spanish postcodes."),

    # ── Datos bancarios y fiscales ────────────────────────────────────────
    Categoria("iban", "Cuentas bancarias (IBAN)", "economico", "#ffb224",
              "Números de cuenta IBAN, con el dígito de control verificado.",
              "Bank accounts (IBAN)",
              "IBAN account numbers, with the check digits verified."),
    Categoria("tarjeta", "Tarjetas de pago", "economico", "#ff801f",
              "Números de tarjeta de crédito o débito, validados con el algoritmo de Luhn.",
              "Payment cards",
              "Credit and debit card numbers, validated with the Luhn algorithm."),
    Categoria("cif", "CIF / NIF de empresa", "economico", "#c99700",
              "Identificación fiscal de empresas y entidades, con control verificado.",
              "Company tax number (CIF/NIF)",
              "Tax identification of companies and bodies, with its check character verified."),

    # ── Datos de salud ────────────────────────────────────────────────────
    Categoria("cip", "CIP / Tarjeta sanitaria", "salud", "#30a46c",
              "CIP-SNS nacional y tarjeta sanitaria autonómica (incluido el formato T.I.S.).",
              "Health card number",
              "Spanish national and regional health card numbers (including the T.I.S. format)."),
    Categoria("nhc", "Nº historia clínica / episodio", "salud", "#12a594",
              "Números de historia, episodio o caso, detectados por contexto.",
              "Medical record / episode no.",
              "Medical record, episode or case numbers, detected from their label."),
    Categoria("nuss", "Nº Seguridad Social (NUSS)", "salud", "#5bb98c",
              "Número de afiliación de 12 dígitos, con dígitos de control verificados.",
              "Social security number",
              "12-digit Spanish social security number, with its check digits verified."),
    Categoria("sanitario", "Nombres del personal sanitario", "salud", "#0d8a5f",
              "Nombres precedidos de Dr./Dra./Fdo./Enf. o cercanos a un nº de colegiado.",
              "Healthcare staff names",
              "Names preceded by Dr/Nurse/Signed or close to a professional registration number."),
    Categoria("colegiado", "Nº de colegiado", "salud", "#86b355",
              "Números de colegiado profesional, detectados por contexto.",
              "Professional registration no.",
              "Professional body registration numbers, detected from their label."),
    Categoria("centro", "Hospital / centro de salud", "salud", "#218358",
              "Nombres de hospitales y centros, incluidas siglas (HUNSC, HUC…).",
              "Hospital / health centre",
              "Names of hospitals and health centres, including their acronyms."),
    Categoria("servicio_unidad", "Servicios y unidades", "salud", "#4cc38a",
              "«Servicio de…», «Unidad de…», «Sección de…» y similares.",
              "Departments and units",
              "«Department of…», «Unit of…», «Section of…» and the like."),

    # ── Expedientes, bienes y vehículos ───────────────────────────────────
    Categoria("expediente", "Expedientes y referencias", "tramites", "#a18072",
              "Nº de expediente, procedimiento judicial, autos, protocolo notarial, "
              "póliza, contrato, factura o pedido, detectados por su etiqueta.",
              "Case files and reference numbers",
              "File, court case, notarial deed, policy, contract, invoice or order "
              "numbers, detected from their label."),
    Categoria("catastro", "Referencias catastrales y fincas", "tramites", "#8d7249",
              "Referencia catastral (20 caracteres) y nº de finca registral.",
              "Land registry references",
              "Spanish cadastral reference (20 characters) and land registry plot numbers."),
    Categoria("matricula", "Matrículas de vehículo", "tramites", "#b5651d",
              "Matrículas españolas, actuales (1234 BCD) y del formato antiguo.",
              "Vehicle number plates",
              "Spanish number plates, both the current format (1234 BCD) and the older one."),

    # ── Organizaciones ────────────────────────────────────────────────────
    Categoria("organizacion", "Empresas y organismos", "organizaciones", "#7a869a",
              "Empresas (S.L., S.A.), juzgados, notarías, universidades y demás "
              "organizaciones citadas en el documento.",
              "Companies and institutions",
              "Companies, courts, notaries, universities and any other organisation "
              "named in the document."),
    Categoria("logo", "Logos y membretes (imágenes)", "organizaciones", "#94a3b8",
              "Imágenes situadas en la cabecera o el pie de página (logotipos).",
              "Logos and letterheads (images)",
              "Images placed in the page header or footer (logotypes)."),

    # ── Otros ─────────────────────────────────────────────────────────────
    Categoria("fecha", "Fechas", "otros", "#918f8a",
              "Todas las demás fechas del documento (asistencia, firma, vencimiento…).",
              "Dates",
              "Every other date in the document (appointments, signature, due date…)."),
    Categoria("personalizada", "Mi lista de términos", "otros", "#63635e",
              "Palabras o frases que tú añadas para redactar siempre.",
              "My own term list",
              "Words or phrases you add yourself to always redact."),
]

CATEGORIAS_POR_ID = {c.id: c for c in CATEGORIAS}

# Categorías activas si el cliente no envía preferencia
IDS_POR_DEFECTO = [c.id for c in CATEGORIAS if c.activa_por_defecto]


def como_dict() -> list[dict]:
    """Serializa las categorías para la API (panel de interruptores).

    Se envían los dos idiomas a la vez: así el catálogo tiene una sola fuente de
    verdad y cambiar de idioma en la interfaz no obliga a volver a pedirlo.
    """
    nombres_es = {g: es for g, es, _ in GRUPOS}
    nombres_en = {g: en for g, _, en in GRUPOS}
    orden = {g: i for i, (g, _, _) in enumerate(GRUPOS)}
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "nombre_en": c.nombre_en or c.nombre,
            "grupo": c.grupo,
            "grupo_nombre": nombres_es.get(c.grupo, c.grupo),
            "grupo_nombre_en": nombres_en.get(c.grupo, c.grupo),
            "orden_grupo": orden.get(c.grupo, 99),
            "color": c.color,
            "descripcion": c.descripcion,
            "descripcion_en": c.descripcion_en or c.descripcion,
            "activa_por_defecto": c.activa_por_defecto,
        }
        for c in CATEGORIAS
    ]
