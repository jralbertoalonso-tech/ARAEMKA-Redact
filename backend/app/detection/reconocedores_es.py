"""Capa 1 — Reconocedores por reglas/regex para identificadores españoles y canarios.

Cada reconocedor emite un tipo de entidad que coincide con el `id` de una
categoría de `categorias.py` (en mayúsculas). Los identificadores con dígitos
o letras de control (DNI, NIE, NUSS) se validan matemáticamente: si el control
no cuadra, el resultado se descarta para reducir falsos positivos.

Los identificadores sin formato público estable (NHC, CIP autonómico,
nº de colegiado, nº de episodio) se detectan POR CONTEXTO: una palabra clave
(«NHC», «CIP», «colegiado»…) seguida del código. Esto está documentado en el
README: es la opción más fiable cuando el formato varía entre centros.
"""

import re

from presidio_analyzer import (
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)

from . import validators


# ──────────────────────────────────────────────────────────────────────────
# Reconocedores con validación de dígitos de control
# ──────────────────────────────────────────────────────────────────────────

class ReconocedorDniNie(PatternRecognizer):
    """DNI (8 dígitos + letra) y NIE (X/Y/Z + 7 dígitos + letra), módulo 23."""

    def __init__(self):
        super().__init__(
            supported_entity="DNI_NIE",
            supported_language="es",
            name="dni_nie_regex",
            patterns=[
                Pattern("dni", r"\b\d{2}[.\s]?\d{3}[.\s]?\d{3}[-\s]?[A-Za-z]\b", 0.4),
                Pattern("nie", r"\b[XYZxyz][-\s]?\d{7}[-\s]?[A-Za-z]\b", 0.4),
            ],
            context=["dni", "nif", "nie", "documento", "identidad"],
        )

    def validate_result(self, pattern_text: str):
        # True → confianza máxima; False → se descarta el resultado
        return validators.validar_dni(pattern_text) or validators.validar_nie(pattern_text)


class ReconocedorNuss(PatternRecognizer):
    """Número de la Seguridad Social: 11-12 dígitos con control módulo 97."""

    def __init__(self):
        super().__init__(
            supported_entity="NUSS",
            supported_language="es",
            name="nuss_regex",
            patterns=[
                # Formatos habituales: 281234567840, 28/12345678/40, 28 1234567840
                Pattern("nuss", r"\b\d{2}[\s/\-.]?\d{7,8}[\s/\-.]?\d{2}\b", 0.3),
            ],
            context=["seguridad", "social", "nuss", "naf", "afiliación", "afiliacion"],
        )

    def validate_result(self, pattern_text: str):
        return validators.validar_nuss(pattern_text)


class ReconocedorTelefono(PatternRecognizer):
    """Teléfonos españoles (móviles 6/7, fijos 8/9), con o sin +34."""

    def __init__(self):
        super().__init__(
            supported_entity="TELEFONO",
            supported_language="es",
            name="telefono_regex",
            patterns=[
                Pattern(
                    # 9 dígitos empezando por 6/7/8/9, con separadores opcionales
                    # entre cualquier par de dígitos (cubre 622 345 678, 622-34-56-78…)
                    "telefono_es",
                    r"(?<![\d/.\-])(?:\+34[\s.\-]?|0034[\s.\-]?)?[6789](?:[\s.\-]?\d){8}(?![\d/])",
                    0.45,
                ),
            ],
            context=["teléfono", "telefono", "tfno", "tel", "móvil", "movil", "contacto", "llamar", "fax"],
        )

    def validate_result(self, pattern_text: str):
        # None mantiene la puntuación del patrón (el contexto puede subirla);
        # False descarta números con prefijo/longitud imposibles en España.
        return None if validators.es_telefono_es(pattern_text) else False


# ──────────────────────────────────────────────────────────────────────────
# Reconocedores por formato sin dígito de control
# ──────────────────────────────────────────────────────────────────────────

class ReconocedorEmail(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="EMAIL",
            supported_language="es",
            name="email_regex",
            patterns=[
                Pattern("email", r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b", 0.85),
            ],
        )


class ReconocedorCipSns(PatternRecognizer):
    """CIP-SNS nacional: 16 caracteres, actualmente BBBBBBBB + 2 letras + 6 dígitos."""

    def __init__(self):
        super().__init__(
            supported_entity="CIP",
            supported_language="es",
            name="cip_sns_regex",
            patterns=[
                Pattern("cip_sns", r"\bB{8}[A-Z]{2}\d{6}\b", 0.9),
                # Forma genérica de 16 alfanuméricos precedida de contexto (ver enhancer)
                Pattern("cip_generico", r"\b[A-Z]{2,10}\d{6,14}\b", 0.2),
            ],
            context=["cip", "tis", "tarjeta", "sanitaria", "sns"],
        )


class ReconocedorFecha(PatternRecognizer):
    """Fechas numéricas y textuales en español."""

    MESES = r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"

    def __init__(self):
        super().__init__(
            supported_entity="FECHA",
            supported_language="es",
            name="fecha_regex",
            patterns=[
                Pattern("fecha_numerica", r"\b\d{1,2}[/\-.]\d{1,2}[/\-.](?:\d{4}|\d{2})\b", 0.6),
                Pattern("fecha_iso", r"\b\d{4}-\d{2}-\d{2}\b", 0.6),
                Pattern(
                    "fecha_textual",
                    rf"\b\d{{1,2}}\s+de\s+{self.MESES}\s+(?:de\s+|del\s+)?\d{{4}}\b",
                    0.75,
                ),
                Pattern("mes_anio", rf"\b{self.MESES}\s+(?:de\s+|del\s+)?\d{{4}}\b", 0.5),
            ],
        )


class ReconocedorEdad(PatternRecognizer):
    """Edades exactas: «47 años», «de 3 meses de edad». Categoría fecha_nacimiento."""

    def __init__(self):
        super().__init__(
            supported_entity="FECHA_NACIMIENTO",
            supported_language="es",
            name="edad_regex",
            patterns=[
                Pattern("edad_anios", r"\b\d{1,3}\s+años(?:\s+de\s+edad)?\b", 0.5),
                Pattern("edad_meses", r"\b\d{1,2}\s+meses\s+de\s+edad\b", 0.6),
            ],
            context=["edad", "paciente", "varón", "varon", "mujer", "niño", "niña"],
        )


class ReconocedorCodigoPostal(PatternRecognizer):
    """Códigos postales españoles. Los canarios (35xxx/38xxx) puntúan más alto."""

    def __init__(self):
        super().__init__(
            supported_entity="LOCALIDAD",
            supported_language="es",
            name="cp_regex",
            patterns=[
                Pattern("cp_canario", r"\b3[58]\d{3}\b", 0.5),
                Pattern("cp_generico", r"\b\d{5}\b", 0.15),  # necesita contexto para superar el umbral
            ],
            context=["cp", "c.p", "código", "postal", "dirección", "direccion", "domicilio", "calle", "municipio"],
        )

    def validate_result(self, pattern_text: str):
        return None if validators.es_codigo_postal_es(pattern_text) else False


class ReconocedorDireccion(PatternRecognizer):
    """Direcciones postales: «C/ Alameda 12», «Avda. Marítima, nº 3, 2ºB»…"""

    VIA = r"(?:C/|C\.|Calle|Avda\.?|Avenida|Av\.|Plaza|Pza\.?|Pl\.|Paseo|Pº|Ctra\.?|Carretera|Camino|Cmno\.?|Urb\.?|Urbanización|Barrio|Bº|Rambla|Travesía|Trva\.?|Lugar)"

    def __init__(self):
        super().__init__(
            supported_entity="DIRECCION",
            supported_language="es",
            name="direccion_regex",
            patterns=[
                Pattern(
                    "via_numero",
                    rf"\b{self.VIA}\s+[A-ZÁÉÍÓÚÑa-záéíóúñ][^,;\n\r]{{2,50}}(?:,?\s*(?:n[ºo°]\.?\s*)?\d+[\wºª°\-]*(?:\s*[,\-]?\s*(?:piso|pta\.?|puerta|esc\.?|bajo|át|atico|ático|izq\.?|dcha\.?|\d+[ºª°][A-Z]?))*)?",
                    0.6,
                ),
            ],
            context=["domicilio", "dirección", "direccion", "residente", "vive"],
        )


class ReconocedorServicioUnidad(PatternRecognizer):
    """Servicios, unidades y secciones hospitalarias."""

    def __init__(self):
        super().__init__(
            supported_entity="SERVICIO_UNIDAD",
            supported_language="es",
            name="servicio_unidad_regex",
            patterns=[
                Pattern(
                    "servicio_de",
                    r"\b(?:Servicio|Unidad|Sección|Seccion|Departamento|Consulta)s?\s+de\s+"
                    r"[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ]*"
                    r"(?:(?:\s*,\s*|\s+y\s+|\s+e\s+|\s+)"
                    r"(?!(?:Paciente|Nombre|Apellidos|Informe|Historia|Fecha|Dr|Dra|Fdo|NHC|DNI|CIP|"
                    r"Ctra|Calle|Avda|Avenida|Plaza|Pza|Paseo|Camino|Urb|Barrio|Tel|Tfno)\b)"
                    r"[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ]*){0,6}",
                    0.55,
                ),
            ],
        )


class ReconocedorCentro(PatternRecognizer):
    """Hospitales y centros de salud: nombres genéricos y siglas canarias conocidas."""

    SIGLAS_CANARIAS = [
        "HUNSC", "HUC", "CHUC", "CHUIMI", "CHUNSC", "HGLP", "HUGCDN", "HIUMI", "SCS",
    ]

    def __init__(self):
        siglas = "|".join(self.SIGLAS_CANARIAS)
        super().__init__(
            supported_entity="CENTRO",
            supported_language="es",
            name="centro_regex",
            patterns=[
                Pattern(
                    # El lookahead negativo evita tragarse la línea siguiente
                    # («… de la Candelaria Servicio de Pediatría»).
                    "hospital_nombre",
                    r"\b(?:Complejo\s+Hospitalario|Hospital(?:\s+Universitario)?|Centro\s+de\s+Salud|Clínica|Consultorio)"
                    r"(?:\s+(?:de\s+|del\s+|de\s+la\s+|de\s+los\s+)?"
                    r"(?!(?:Servicio|Unidad|Sección|Seccion|Departamento|Consulta|Gerencia|Paciente|Nombre|Apellidos|Informe|Historia|Fecha|Tel[eé]fono|Tel|Tfno|NHC|DNI|CIP|"
                    r"Ctra|Calle|Avda|Avenida|Plaza|Pza|Paseo|Camino|Urb|Barrio)\b)"
                    r"[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\-]*){1,7}",
                    0.6,
                ),
                Pattern("siglas_canarias", rf"\b(?:{siglas})\b", 0.7),
                Pattern(
                    "servicio_canario",
                    r"\bServicio\s+Canario\s+de\s+(?:la\s+)?Salud\b|\bGerencia\s+de\s+(?:Atención\s+Primaria|Servicios\s+Sanitarios)[^\n,;]{0,40}",
                    0.75,
                ),
            ],
        )


class ReconocedorFirmaSanitario(PatternRecognizer):
    """Nombres tras tratamiento profesional o firma: Dr./Dra./Fdo.:/Enf. …"""

    TRATAMIENTO = r"(?:Dr[a]?\.?|Doctor[a]?|Fdo\.?\s*:?|Firmado\s*:?|Enf\.?|D\.U\.E\.?|Prof\.?|Lcdo\.?|Lcda\.?|Ldo\.?|Lda\.?)"
    NOMBRE = r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?:\s+(?:de\s+|del\s+|de\s+la\s+|[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+|[A-ZÁÉÍÓÚÑ]\.)){1,4}"

    def __init__(self):
        super().__init__(
            supported_entity="SANITARIO",
            supported_language="es",
            name="firma_sanitario_regex",
            patterns=[
                Pattern("tratamiento_nombre", rf"\b{self.TRATAMIENTO}\s+{self.NOMBRE}", 0.7),
            ],
        )


class ReconocedorSexo(PatternRecognizer):
    """Menciones explícitas del sexo del paciente (desactivada por defecto)."""

    def __init__(self):
        super().__init__(
            supported_entity="SEXO",
            supported_language="es",
            name="sexo_regex",
            patterns=[
                Pattern("sexo_etiqueta", r"(?i)\bsexo\s*:?\s*(?:varón|varon|mujer|hombre|masculino|femenino|[VMH])\b", 0.85),
                Pattern("sexo_frase", r"(?i)\b(?:varón|varon|mujer|niño|niña)\s+de\s+\d{1,3}\s+(?:años|meses)\b", 0.5),
            ],
        )


# ──────────────────────────────────────────────────────────────────────────
# Reconocedores por contexto (formato variable entre centros/CCAA)
# ──────────────────────────────────────────────────────────────────────────

class ReconocedorPorContexto(EntityRecognizer):
    """Detecta códigos cuyo formato varía: una etiqueta conocida seguida del valor.

    Solo se redacta el VALOR (grupo 1 del regex), no la etiqueta, para que el
    documento siga siendo legible («NHC: ████» en lugar de «██████████»).
    """

    def __init__(self, entidad: str, nombre: str, regex: str, confianza: float,
                 flags: int = re.IGNORECASE):
        super().__init__(
            supported_entities=[entidad],
            supported_language="es",
            name=nombre,
        )
        self.regex = re.compile(regex, flags)
        self.confianza = confianza

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        resultados = []
        for m in self.regex.finditer(text):
            inicio, fin = m.span(1)  # solo el valor, no la etiqueta
            if inicio == fin:
                continue
            resultados.append(
                RecognizerResult(
                    entity_type=self.supported_entities[0],
                    start=inicio,
                    end=fin,
                    score=self.confianza,
                    analysis_explanation=None,
                    recognition_metadata={
                        RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                        RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                    },
                )
            )
        return resultados


# Secuencia de nombre propio: «María del Carmen Pérez Rodríguez»,
# «PÉREZ RODRÍGUEZ, MARÍA» (formato de listados), con partículas de/del/la/y.
_NOMBRE_PROPIO = (
    r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+"
    r"(?:[ ,]+(?:(?:de|del|la|las|los|y)\s+)*"
    r"(?!(?:DNI|NIE|NHC|CIP|NUSS|TIS|Tel|Tfno|Sexo|Edad|Fecha|Domicilio|Correo|Historia|Episodio)\b)"
    r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+){1,6}"
)


def crear_reconocedores_contexto() -> list[EntityRecognizer]:
    """Reconocedores etiqueta→valor para NHC, episodio, CIP autonómico y colegiado."""
    return [
        # Nombre del paciente etiquetado: «Paciente: María Pérez…», «Apellidos y nombre: …»
        # No depende del NER: es la vía más fiable en informes con membrete.
        ReconocedorPorContexto(
            "PERSON", "paciente_etiquetado",
            rf"(?i:\b(?:paciente|nombre(?:\s+(?:del?\s+paciente|y\s+apellidos))?|apellidos(?:\s+y\s+nombre)?))"
            rf"\s*:\s*({_NOMBRE_PROPIO})",
            0.85,
            flags=0,
        ),
        # Tratamientos civiles: «D. / Dña. / Don / Doña / Sr. / Sra.» + nombre
        # (familiares y acompañantes; los sanitarios van con Dr./Dra./Fdo.)
        ReconocedorPorContexto(
            "PERSON", "tratamiento_civil",
            rf"\b(?:D\.|Dña\.|Don|Doña|Sr\.?|Sra\.?)\s+({_NOMBRE_PROPIO})",
            0.7,
            flags=0,
        ),
        # Nº de historia clínica: «NHC: 123456», «Historia clínica nº 123456», «Hª 123456»
        ReconocedorPorContexto(
            "NHC", "nhc_contexto",
            r"(?:\bN\.?H\.?C\.?|\bn[ºo°]?\s*(?:de\s+)?historia(?:\s+cl[ií]nica)?|historia\s+cl[ií]nica|\bH\.?ª|\bHC\b)"
            r"\s*(?:n[ºo°]\.?|:|\.)?\s*([A-Z]{0,3}[\s\-/]?\d{2,12}(?:[\-/]\d{1,10})?)",
            0.75,
        ),
        # Nº de episodio, caso o proceso asistencial (admite 2024-118332, EP/44821…)
        ReconocedorPorContexto(
            "NHC", "episodio_contexto",
            r"(?:\bepisodio|\bcaso|\bproceso|\bingreso)\s*(?:n[ºo°]\.?|:)?\s*([A-Z]{0,3}[\s\-/]?\d{4,12}(?:[\-/]\d{1,10})?)",
            0.6,
        ),
        # CIP autonómico / tarjeta sanitaria: «CIP: 1234567890», «TIS ABCD123456»,
        # «T.I.S: 987654321» (variante con puntos usada en algunos hospitales)
        ReconocedorPorContexto(
            "CIP", "cip_contexto",
            r"(?:\bCIP(?:[\s\-]?(?:AUT|SNS|SCS))?|\bT\.?I\.?S\.?(?![A-Za-z])|\bCIPA\b|tarjeta\s+sanitaria)"
            r"\s*(?:n[ºo°]\.?|:)?\s*([A-Z]{0,10}\d{6,16})",
            0.8,
        ),
        # Nº de colegiado: «Nº Col.: 38/38/12345», «Colegiado 12345»
        ReconocedorPorContexto(
            "COLEGIADO", "colegiado_contexto",
            r"(?:\bn[ºo°]?\.?\s*(?:de\s+)?col(?:\.|egiad[oa])?|\bcolegiad[oa])"
            r"\s*(?:n[ºo°]\.?|:)?\s*(\d{2,9}(?:[/\-]\d{1,9}){0,3})",
            0.8,
        ),
        # Fecha de nacimiento etiquetada: «F. Nac.: 01/02/1980», «Fecha de nacimiento: …»
        ReconocedorPorContexto(
            "FECHA_NACIMIENTO", "fnac_contexto",
            r"(?:f(?:echa)?\.?\s*(?:de\s+)?nac(?:\.|imiento)?|nacid[oa]\s+el)"
            r"\s*:?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.](?:\d{4}|\d{2})|\d{1,2}\s+de\s+\w+\s+(?:de\s+)?\d{4})",
            0.85,
        ),
    ]


def crear_reconocedor_personalizado(terminos: list[str]) -> PatternRecognizer | None:
    """Reconocedor con la lista de términos del usuario (coincidencia literal)."""
    terminos = [t.strip() for t in terminos if t and t.strip()]
    if not terminos:
        return None
    return PatternRecognizer(
        supported_entity="PERSONALIZADA",
        supported_language="es",
        name="lista_personalizada",
        deny_list=terminos,
        deny_list_score=1.0,
    )


def crear_reconocedores_regex() -> list[PatternRecognizer]:
    """Instancia todos los reconocedores de la capa 1."""
    return [
        ReconocedorDniNie(),
        ReconocedorNuss(),
        ReconocedorTelefono(),
        ReconocedorEmail(),
        ReconocedorCipSns(),
        ReconocedorFecha(),
        ReconocedorEdad(),
        ReconocedorCodigoPostal(),
        ReconocedorDireccion(),
        ReconocedorServicioUnidad(),
        ReconocedorCentro(),
        ReconocedorFirmaSanitario(),
        ReconocedorSexo(),
    ]
