"""Capa 1 — Reconocedores por reglas para documentos en INGLÉS (Reino Unido y EE. UU.).

Reflejan la estructura de `reconocedores_es.py` pero con los identificadores
anglosajones: número del NHS, National Insurance (NINO), Social Security (SSN),
ITIN, códigos postales y teléfonos de UK/EE. UU., además de los internacionales
(IBAN, tarjetas, pasaporte, correo). Los que llevan control (NHS, SSN, ITIN,
tarjeta, IBAN) se validan matemáticamente.

Cada reconocedor emite un tipo de entidad que coincide con el `id` de una
categoría de `categorias.py` (en mayúsculas). Su `supported_language` es "en".

Los códigos sin formato público estable (historia clínica, expediente) se
detectan POR CONTEXTO: una etiqueta conocida («MRN», «Case No.», «DOB»…)
seguida del valor.
"""

import re

from presidio_analyzer import Pattern, PatternRecognizer

from . import validators
from .reconocedores_es import ReconocedorPorContexto


# ──────────────────────────────────────────────────────────────────────────
# Con validación de dígitos/formato de control
# ──────────────────────────────────────────────────────────────────────────

class ReconocedorNhs(PatternRecognizer):
    """Número del NHS británico: 10 dígitos (3-3-4) con control módulo 11."""

    def __init__(self):
        super().__init__(
            supported_entity="NHS",
            supported_language="en",
            name="nhs_regex",
            patterns=[
                Pattern("nhs", r"\b\d{3}[\s\-]?\d{3}[\s\-]?\d{4}\b", 0.3),
            ],
            context=["nhs", "patient", "health"],
        )

    def validate_result(self, pattern_text: str):
        return validators.validar_nhs(pattern_text)


class ReconocedorNino(PatternRecognizer):
    """National Insurance Number: 2 letras + 6 dígitos + 1 letra (A-D)."""

    def __init__(self):
        super().__init__(
            supported_entity="NINO",
            supported_language="en",
            name="nino_regex",
            patterns=[
                Pattern("nino", r"\b[A-Za-z]{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?[A-Da-d]\b", 0.4),
            ],
            context=["national", "insurance", "ni", "nino"],
        )

    def validate_result(self, pattern_text: str):
        return validators.es_nino(pattern_text)


class ReconocedorSsn(PatternRecognizer):
    """Social Security Number (EE. UU.): AAA-GG-SSSS, con rangos válidos."""

    def __init__(self):
        super().__init__(
            supported_entity="SSN",
            supported_language="en",
            name="ssn_regex",
            patterns=[
                # Con guiones/espacios explícitos: patrón fiable.
                Pattern("ssn_sep", r"\b\d{3}[\s\-]\d{2}[\s\-]\d{4}\b", 0.45),
                # Nueve dígitos seguidos: más ambiguo, se apoya en la validación.
                Pattern("ssn_junto", r"\b\d{9}\b", 0.2),
            ],
            context=["ssn", "social", "security", "taxpayer"],
        )

    def validate_result(self, pattern_text: str):
        # ITIN se reconoce aparte; aquí solo SSN «de verdad».
        return validators.es_ssn(pattern_text) and not validators.es_itin(pattern_text)


class ReconocedorItin(PatternRecognizer):
    """ITIN estadounidense (empieza por 9, grupo en rangos reservados)."""

    def __init__(self):
        super().__init__(
            supported_entity="SSN",       # misma categoría que el SSN
            supported_language="en",
            name="itin_regex",
            patterns=[
                Pattern("itin", r"\b9\d{2}[\s\-]?\d{2}[\s\-]?\d{4}\b", 0.4),
            ],
            context=["itin", "taxpayer", "individual", "tax"],
        )

    def validate_result(self, pattern_text: str):
        return validators.es_itin(pattern_text)


class ReconocedorIbanEn(PatternRecognizer):
    """IBAN (cualquier país) con control módulo 97 — versión en inglés."""

    def __init__(self):
        super().__init__(
            supported_entity="IBAN",
            supported_language="en",
            name="iban_regex_en",
            global_regex_flags=re.MULTILINE | re.DOTALL,
            patterns=[
                Pattern("iban_numerico", r"\b[A-Z]{2}\d{2}(?:[\s\-]?\d{4}){2,7}(?:[\s\-]?\d{1,3})?\b", 0.5),
                Pattern("iban_alfanumerico", r"\b[A-Z]{2}\d{2}[A-Z]{4}(?:[\s\-]?[A-Z0-9]{4}){2,6}\b", 0.5),
            ],
            context=["iban", "account", "bank", "sort", "transfer"],
        )

    def validate_result(self, pattern_text: str):
        return validators.validar_iban(pattern_text)


class ReconocedorTarjetaEn(PatternRecognizer):
    """Tarjetas de pago (Luhn) — versión en inglés."""

    def __init__(self):
        super().__init__(
            supported_entity="TARJETA",
            supported_language="en",
            name="tarjeta_regex_en",
            patterns=[
                Pattern("tarjeta", r"\b[3-6]\d{3}(?:[\s\-]?\d{4}){2}[\s\-]?\d{1,7}\b", 0.5),
            ],
            context=["card", "visa", "mastercard", "amex", "credit", "debit", "payment"],
        )

    def validate_result(self, pattern_text: str):
        return validators.validar_tarjeta(pattern_text)


# ──────────────────────────────────────────────────────────────────────────
# Por formato sin dígito de control
# ──────────────────────────────────────────────────────────────────────────

class ReconocedorEmailEn(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="EMAIL",
            supported_language="en",
            name="email_regex_en",
            patterns=[Pattern("email", r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b", 0.85)],
        )


class ReconocedorTelefonoEn(PatternRecognizer):
    """Teléfonos británicos y norteamericanos, con +44 / +1 opcional."""

    def __init__(self):
        super().__init__(
            supported_entity="TELEFONO",
            supported_language="en",
            name="telefono_regex_en",
            patterns=[
                # EE. UU./Canadá: (415) 555-2671, 415-555-2671, +1 415 555 2671
                Pattern("tel_us", r"(?<![\d/.\-])(?:\+1[\s.\-]?)?\(?[2-9]\d{2}\)?[\s.\-]?[2-9]\d{2}[\s.\-]?\d{4}(?![\d/])", 0.4),
                # Reino Unido: 020 7946 0958, +44 20 7946 0958, 07700 900123
                Pattern("tel_uk", r"(?<![\d/.\-])(?:\+44[\s.\-]?|0)(?:\d[\s.\-]?){9,10}(?![\d/])", 0.4),
            ],
            context=["phone", "tel", "telephone", "mobile", "cell", "call", "fax", "contact"],
        )

    def validate_result(self, pattern_text: str):
        if validators.es_telefono_us(pattern_text) or validators.es_telefono_uk(pattern_text):
            return None       # mantiene la puntuación (el contexto puede subirla)
        return False


class ReconocedorCodigoPostalEn(PatternRecognizer):
    """Códigos postales británicos (SW1A 1AA) y ZIP estadounidenses (90210-1234)."""

    def __init__(self):
        super().__init__(
            supported_entity="LOCALIDAD",
            supported_language="en",
            name="postcode_regex_en",
            patterns=[
                Pattern("uk_postcode", r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", 0.6),
                Pattern("us_zip", r"\b\d{5}-\d{4}\b", 0.55),  # ZIP+4: inequívoco
            ],
            context=["postcode", "zip", "postal", "address"],
        )

    def validate_result(self, pattern_text: str):
        return validators.es_codigo_postal_uk(pattern_text) or validators.es_zip_us(pattern_text)


class ReconocedorDireccionEn(PatternRecognizer):
    """Direcciones postales inglesas: «12 Oak Street», «1600 Pennsylvania Avenue»."""

    def __init__(self):
        super().__init__(
            supported_entity="DIRECCION",
            supported_language="en",
            name="direccion_regex_en",
            patterns=[
                Pattern(
                    "calle_en",
                    r"\b\d{1,5}[A-Za-z]?\s+(?:[A-Z][a-z]+\s){1,4}"
                    r"(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd|"
                    r"Court|Ct|Place|Pl|Square|Sq|Way|Close|Crescent|Terrace|Gardens|Row)\b\.?",
                    0.5,
                ),
            ],
            context=["address", "street", "avenue", "road", "residing", "lives"],
        )


class ReconocedorFechaEn(PatternRecognizer):
    """Fechas en formatos ingleses.

    Cubre el numérico (MM/DD/YYYY y DD/MM/YYYY — ambiguos, se tratan igual a
    efectos de detección) y el textual inglés: «January 5, 2024», «5 Jan 2024»,
    «2024-01-05».
    """

    _MESES = (r"January|February|March|April|May|June|July|August|September|"
              r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")

    def __init__(self):
        super().__init__(
            supported_entity="FECHA",
            supported_language="en",
            name="fecha_regex_en",
            patterns=[
                Pattern("fecha_num", r"\b\d{1,2}[/\-.]\d{1,2}[/\-.](?:\d{4}|\d{2})\b", 0.4),
                Pattern("fecha_iso", r"\b\d{4}-\d{2}-\d{2}\b", 0.5),
                Pattern("fecha_texto_md", rf"\b(?:{self._MESES})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b", 0.6),
                Pattern("fecha_texto_dm", rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{self._MESES})\.?,?\s+\d{{4}}\b", 0.6),
                # Mes y año, sin día: «April 2024», «Jan 2024»
                Pattern("fecha_mes_anio", rf"\b(?:{self._MESES})\.?\s+\d{{4}}\b", 0.45),
            ],
            context=["date", "dated", "on", "signed", "issued", "due", "expiry", "expires"],
        )


class ReconocedorEdadEn(PatternRecognizer):
    """Edades en inglés: «47 years old», «aged 47», «47-year-old»."""

    def __init__(self):
        super().__init__(
            supported_entity="FECHA_NACIMIENTO",
            supported_language="en",
            name="edad_regex_en",
            patterns=[
                Pattern("edad_yo", r"\b\d{1,3}\s*[\-\s]?years?[\-\s]old\b", 0.55),
                Pattern("edad_aged", r"\baged\s+\d{1,3}\b", 0.55),
            ],
            context=["age", "aged", "old", "patient"],
        )


class ReconocedorOrganizacionEn(PatternRecognizer):
    """Empresas y organismos ingleses: «Acme Ltd», «Globex Inc.», «… LLC», tribunales."""

    def __init__(self):
        super().__init__(
            supported_entity="ORGANIZACION",
            supported_language="en",
            name="organizacion_regex_en",
            global_regex_flags=re.MULTILINE | re.DOTALL,
            patterns=[
                # Nombre propio seguido de forma societaria. El nombre no puede
                # empezar por un tratamiento (Dr./Mr.…) ni contener puntos, para
                # no tragarse «Dr. Emily Carter. Hospital» como si fuera una
                # empresa terminada en «Hospital» (era un falso positivo real).
                Pattern(
                    "sociedad_en",
                    r"\b(?!(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Sir|Dame|Lord|Lady)\b)"
                    r"(?:[A-Z][A-Za-z&'’\-]+\s){1,5}"
                    r"(?:Ltd|Limited|LLP|LLC|Inc|Incorporated|Corp|Corporation|"
                    r"Company|Co|PLC|plc|Group|Holdings|Partners|Associates|"
                    r"Trust|Foundation|University|Hospital|Clinic|Bank)\b\.?",
                    0.45,
                ),
                # Tribunales y organismos
                Pattern(
                    "tribunal_en",
                    r"\b(?:the\s+)?(?:High|Crown|County|Magistrates'?|Supreme|District|"
                    r"Circuit|Family|Superior)\s+Court(?:\s+of\s+[A-Z][A-Za-z\s]+?)?\b",
                    0.5,
                ),
            ],
            context=["company", "court", "hospital", "university", "ltd", "inc", "llc"],
        )


# ──────────────────────────────────────────────────────────────────────────
# Fábricas (mismas firmas que reconocedores_es)
# ──────────────────────────────────────────────────────────────────────────

# Secuencia de nombre propio en inglés (permite guiones y apóstrofos: O'Brien,
# Smith-Jones), con partícula opcional «van/von/de/la».
_NOMBRE_PROPIO_EN = (
    r"[A-Z][A-Za-z'’\-]+"
    r"(?:\s+(?:(?:van|von|de|del|la|le|di|da|of)\s+)*"
    r"[A-Z][A-Za-z'’\-]+){1,4}"
)


def crear_reconocedores_regex_en() -> list[PatternRecognizer]:
    """Instancia los reconocedores de la capa 1 en inglés."""
    return [
        ReconocedorNhs(),
        ReconocedorNino(),
        ReconocedorSsn(),
        ReconocedorItin(),
        ReconocedorIbanEn(),
        ReconocedorTarjetaEn(),
        ReconocedorEmailEn(),
        ReconocedorTelefonoEn(),
        ReconocedorCodigoPostalEn(),
        ReconocedorDireccionEn(),
        ReconocedorFechaEn(),
        ReconocedorEdadEn(),
        ReconocedorOrganizacionEn(),
    ]


def crear_reconocedores_contexto_en() -> list:
    """Reconocedores etiqueta→valor en inglés (nombre por rol, MRN, DOB, expediente…)."""
    return [
        # Nombre precedido de su rol: «Patient: John Smith», «Claimant: …»
        ReconocedorPorContexto(
            "PERSON", "nombre_etiquetado_en",
            rf"(?i:\b(?:patient|name|full\s+name|client|claimant|defendant|"
            rf"plaintiff|complainant|applicant|appellant|respondent|witness|"
            rf"employee|employer|tenant|landlord|buyer|seller|purchaser|vendor|"
            rf"owner|holder|beneficiary|insured|policyholder|customer|"
            rf"signatory|attorney|guardian|next\s+of\s+kin|referred\s+by|"
            rf"attention|attn))"
            rf"\s*:\s*({_NOMBRE_PROPIO_EN})",
            0.85,
            flags=0,
        ),
        # Tratamientos: «Mr / Mrs / Ms / Miss / Dr / Prof» + nombre
        ReconocedorPorContexto(
            "PERSON", "tratamiento_en",
            rf"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Sir|Dame|Lord|Lady)\.?\s+({_NOMBRE_PROPIO_EN})",
            0.7,
            flags=0,
        ),
        # Personal sanitario: «Dr. Jane Roe», «signed by … , MD/RN»
        ReconocedorPorContexto(
            "SANITARIO", "sanitario_en",
            rf"\b(?:Dr|Doctor|Consultant|Physician|Surgeon|Nurse)\.?\s+({_NOMBRE_PROPIO_EN})",
            0.7,
            flags=0,
        ),
        # Historia clínica: «MRN: 12345», «Medical Record No. 12345», «Hospital No»
        ReconocedorPorContexto(
            "NHC", "mrn_en",
            r"(?:\bM\.?R\.?N\.?|medical\s+record(?:\s+(?:no|number|#))?|"
            r"hospital\s+(?:no|number)|record\s+(?:no|number)|chart\s+(?:no|number))"
            r"\s*(?:no\.?|#|:)?\s*([A-Z]{0,3}[\s\-]?\d{4,12}(?:[\-/]\d{1,10})?)",
            0.75,
        ),
        # Fecha de nacimiento: «DOB: 05/01/1980», «Date of Birth: …», «born on …»
        ReconocedorPorContexto(
            "FECHA_NACIMIENTO", "dob_en",
            r"(?:\bD\.?O\.?B\.?|date\s+of\s+birth|born(?:\s+on)?)"
            r"\s*:?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.](?:\d{4}|\d{2})|"
            r"\d{4}-\d{2}-\d{2}|"
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
            r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})",
            0.85,
        ),
        # Expediente / referencia: «Case No.», «File No.», «Invoice #», «Ref:», «Policy No.»
        ReconocedorPorContexto(
            "EXPEDIENTE", "expediente_en",
            r"(?:\bcase|\bfile|\bclaim|\bmatter|\binvoice|\border|\bpolicy|"
            r"\bcontract|\breference|\bref|\bpurchase\s+order|\bp\.?o\.?|\bdocket)"
            r"\s*(?:no\.?|number|#|:)?\s*"
            r"([A-Z]{0,6}[\s\-/]?\d{2,}(?:[\-/.]\d{1,6}){0,4}(?:[\-/][A-Z]{1,4})?)",
            0.7,
        ),
        # Pasaporte por etiqueta
        ReconocedorPorContexto(
            "PASAPORTE", "pasaporte_en",
            r"(?:\bpassport)\s*(?:no\.?|number|#|:)?\s*([A-Z0-9]{6,9})",
            0.85,
        ),
    ]
