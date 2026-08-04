"""Definición de las categorías de datos personales que la aplicación detecta.

Cada categoría tiene un identificador estable (se usa en la API y en los
perfiles), un nombre visible en español, un grupo (para el panel de
interruptores) y un color (para el resaltado en la vista de verificación).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Categoria:
    id: str            # identificador estable usado por la API
    nombre: str        # nombre visible para el usuario
    grupo: str         # grupo del panel: paciente | institucional | sanitario | otros
    color: str         # color de resaltado en la vista de verificación
    descripcion: str   # texto de ayuda del interruptor
    activa_por_defecto: bool = True


CATEGORIAS: list[Categoria] = [
    # ── Datos del paciente ────────────────────────────────────────────────
    Categoria("persona", "Nombres de personas (paciente y familiares)", "paciente", "#e5484d",
              "Nombres y apellidos detectados que no parecen personal sanitario."),
    Categoria("dni_nie", "DNI / NIE", "paciente", "#d6409f",
              "Documento nacional de identidad o NIE, con letra de control verificada."),
    Categoria("nuss", "Nº Seguridad Social (NUSS)", "paciente", "#ab4aba",
              "Número de afiliación de 12 dígitos, con dígitos de control verificados."),
    Categoria("cip", "CIP / Tarjeta sanitaria", "paciente", "#8e4ec6",
              "CIP-SNS nacional y código de tarjeta sanitaria (SCS y otras CCAA), detectado por formato o por contexto."),
    Categoria("nhc", "Nº historia clínica / episodio", "paciente", "#6e56cf",
              "Números de historia, episodio o caso, detectados por contexto (NHC, Hª, episodio…)."),
    Categoria("fecha_nacimiento", "Fecha de nacimiento y edad", "paciente", "#5b5bd6",
              "Fechas junto a «nacimiento/nacido» y edades exactas («47 años»)."),
    Categoria("sexo", "Sexo", "paciente", "#3e63dd",
              "Menciones explícitas de sexo (varón/mujer/hombre) junto a datos del paciente.",
              activa_por_defecto=False),
    Categoria("direccion", "Direcciones postales", "paciente", "#0090ff",
              "Calles, avenidas y domicilios detectados por patrón o por el modelo de lenguaje."),
    Categoria("telefono", "Teléfonos", "paciente", "#00a2c7",
              "Teléfonos españoles (móviles y fijos), con prefijo y longitud validados."),
    Categoria("email", "Correos electrónicos", "paciente", "#12a594",
              "Direcciones de correo electrónico."),

    # ── Datos institucionales ─────────────────────────────────────────────
    Categoria("centro", "Hospital / centro de salud", "institucional", "#30a46c",
              "Nombres de hospitales y centros, incluidas siglas (HUNSC, HUC, CHUIMI…)."),
    Categoria("servicio_unidad", "Servicios y unidades", "institucional", "#46a758",
              "«Servicio de…», «Unidad de…», «Sección de…» y similares."),
    Categoria("logo", "Logos y membretes (imágenes)", "institucional", "#30a46c",
              "Imágenes situadas en la cabecera o el pie de página (logotipos del centro)."),

    # ── Personal sanitario ────────────────────────────────────────────────
    Categoria("sanitario", "Nombres del personal sanitario", "sanitario", "#f76b15",
              "Nombres precedidos de Dr./Dra./Fdo./Enf. o cercanos a un nº de colegiado."),
    Categoria("colegiado", "Nº de colegiado", "sanitario", "#ffb224",
              "Números de colegiado detectados por contexto («Nº col.», «colegiado»)."),

    # ── Otros ─────────────────────────────────────────────────────────────
    Categoria("fecha", "Fechas de asistencia", "otros", "#a18072",
              "Todas las demás fechas del documento (ingresos, consultas, informes…)."),
    Categoria("localidad", "Localidades y códigos postales", "otros", "#918f8a",
              "Nombres de lugar y códigos postales españoles (35xxx/38xxx incluidos)."),
    Categoria("personalizada", "Mi lista de términos", "otros", "#63635e",
              "Palabras o frases que tú añadas para redactar siempre."),
]

CATEGORIAS_POR_ID = {c.id: c for c in CATEGORIAS}

# Categorías activas si el cliente no envía preferencia
IDS_POR_DEFECTO = [c.id for c in CATEGORIAS if c.activa_por_defecto]


def como_dict() -> list[dict]:
    """Serializa las categorías para la API (panel de interruptores)."""
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "grupo": c.grupo,
            "color": c.color,
            "descripcion": c.descripcion,
            "activa_por_defecto": c.activa_por_defecto,
        }
        for c in CATEGORIAS
    ]
