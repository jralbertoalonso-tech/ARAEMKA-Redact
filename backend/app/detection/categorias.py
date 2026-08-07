"""Catálogo de datos personales que la aplicación detecta.

AnoniPRO es de uso general: sirve para documentos clínicos, jurídicos,
laborales, facturas y papeles personales. Cada categoría tiene un identificador
estable (se usa en la API y en los perfiles), un nombre visible en español, un
grupo (para el panel de interruptores) y un color (para el resaltado).
"""

from dataclasses import dataclass

# Grupos del panel, en el orden en que se muestran.
GRUPOS = [
    ("identidad", "Personas e identidad"),
    ("contacto", "Contacto y ubicación"),
    ("economico", "Datos bancarios y fiscales"),
    ("salud", "Datos de salud"),
    ("tramites", "Expedientes, bienes y vehículos"),
    ("organizaciones", "Organizaciones"),
    ("otros", "Otros"),
]


@dataclass(frozen=True)
class Categoria:
    id: str            # identificador estable usado por la API
    nombre: str        # nombre visible para el usuario
    grupo: str         # grupo del panel (ver GRUPOS)
    color: str         # color de resaltado en la vista de verificación
    descripcion: str   # texto de ayuda del interruptor
    activa_por_defecto: bool = True


CATEGORIAS: list[Categoria] = [
    # ── Personas e identidad ──────────────────────────────────────────────
    Categoria("persona", "Nombres de personas", "identidad", "#e5484d",
              "Nombres y apellidos de cualquier persona: interesados, clientes, "
              "familiares, empleados…"),
    Categoria("dni_nie", "DNI / NIE", "identidad", "#d6409f",
              "Documento nacional de identidad o NIE, con letra de control verificada."),
    Categoria("pasaporte", "Pasaporte", "identidad", "#ab4aba",
              "Números de pasaporte (formato español), detectados por contexto."),
    Categoria("fecha_nacimiento", "Fecha de nacimiento y edad", "identidad", "#8e4ec6",
              "Fechas junto a «nacimiento/nacido» y edades exactas («47 años»)."),
    Categoria("sexo", "Sexo", "identidad", "#6e56cf",
              "Menciones explícitas de sexo (varón/mujer/hombre).",
              activa_por_defecto=False),

    # ── Contacto y ubicación ──────────────────────────────────────────────
    Categoria("direccion", "Direcciones postales", "contacto", "#3e63dd",
              "Calles, avenidas y domicilios detectados por patrón o por el modelo de lenguaje."),
    Categoria("telefono", "Teléfonos", "contacto", "#0090ff",
              "Teléfonos españoles (móviles y fijos), con prefijo y longitud validados."),
    Categoria("email", "Correos electrónicos", "contacto", "#00a2c7",
              "Direcciones de correo electrónico."),
    Categoria("localidad", "Localidades y códigos postales", "contacto", "#7d9bf5",
              "Nombres de lugar y códigos postales españoles."),

    # ── Datos bancarios y fiscales ────────────────────────────────────────
    Categoria("iban", "Cuentas bancarias (IBAN)", "economico", "#ffb224",
              "Números de cuenta IBAN, con el dígito de control verificado."),
    Categoria("tarjeta", "Tarjetas de pago", "economico", "#ff801f",
              "Números de tarjeta de crédito o débito, validados con el algoritmo de Luhn."),
    Categoria("cif", "CIF / NIF de empresa", "economico", "#c99700",
              "Identificación fiscal de empresas y entidades, con control verificado."),

    # ── Datos de salud ────────────────────────────────────────────────────
    Categoria("cip", "CIP / Tarjeta sanitaria", "salud", "#30a46c",
              "CIP-SNS nacional y tarjeta sanitaria autonómica (incluido el formato T.I.S.)."),
    Categoria("nhc", "Nº historia clínica / episodio", "salud", "#12a594",
              "Números de historia, episodio o caso, detectados por contexto."),
    Categoria("nuss", "Nº Seguridad Social (NUSS)", "salud", "#5bb98c",
              "Número de afiliación de 12 dígitos, con dígitos de control verificados."),
    Categoria("sanitario", "Nombres del personal sanitario", "salud", "#0d8a5f",
              "Nombres precedidos de Dr./Dra./Fdo./Enf. o cercanos a un nº de colegiado."),
    Categoria("colegiado", "Nº de colegiado", "salud", "#86b355",
              "Números de colegiado profesional, detectados por contexto."),
    Categoria("centro", "Hospital / centro de salud", "salud", "#218358",
              "Nombres de hospitales y centros, incluidas siglas (HUNSC, HUC…)."),
    Categoria("servicio_unidad", "Servicios y unidades", "salud", "#4cc38a",
              "«Servicio de…», «Unidad de…», «Sección de…» y similares."),

    # ── Expedientes, bienes y vehículos ───────────────────────────────────
    Categoria("expediente", "Expedientes y referencias", "tramites", "#a18072",
              "Nº de expediente, procedimiento judicial, autos, protocolo notarial, "
              "póliza, contrato, factura o pedido, detectados por su etiqueta."),
    Categoria("catastro", "Referencias catastrales y fincas", "tramites", "#8d7249",
              "Referencia catastral (20 caracteres) y nº de finca registral."),
    Categoria("matricula", "Matrículas de vehículo", "tramites", "#b5651d",
              "Matrículas españolas, actuales (1234 BCD) y del formato antiguo."),

    # ── Organizaciones ────────────────────────────────────────────────────
    Categoria("organizacion", "Empresas y organismos", "organizaciones", "#7a869a",
              "Empresas (S.L., S.A.), juzgados, notarías, universidades y demás "
              "organizaciones citadas en el documento."),
    Categoria("logo", "Logos y membretes (imágenes)", "organizaciones", "#94a3b8",
              "Imágenes situadas en la cabecera o el pie de página (logotipos)."),

    # ── Otros ─────────────────────────────────────────────────────────────
    Categoria("fecha", "Fechas", "otros", "#918f8a",
              "Todas las demás fechas del documento (asistencia, firma, vencimiento…)."),
    Categoria("personalizada", "Mi lista de términos", "otros", "#63635e",
              "Palabras o frases que tú añadas para redactar siempre."),
]

CATEGORIAS_POR_ID = {c.id: c for c in CATEGORIAS}

# Categorías activas si el cliente no envía preferencia
IDS_POR_DEFECTO = [c.id for c in CATEGORIAS if c.activa_por_defecto]


def como_dict() -> list[dict]:
    """Serializa las categorías para la API (panel de interruptores)."""
    nombres_grupo = dict(GRUPOS)
    orden_grupo = {g: i for i, (g, _) in enumerate(GRUPOS)}
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "grupo": c.grupo,
            "grupo_nombre": nombres_grupo.get(c.grupo, c.grupo),
            "orden_grupo": orden_grupo.get(c.grupo, 99),
            "color": c.color,
            "descripcion": c.descripcion,
            "activa_por_defecto": c.activa_por_defecto,
        }
        for c in CATEGORIAS
    ]
