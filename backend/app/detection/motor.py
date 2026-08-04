"""Motor de detección: orquesta la capa 1 (reglas) y la capa 2 (NER spaCy).

Construye un único AnalyzerEngine de Presidio con:
  - los reconocedores regex/contexto españoles (capa 1), y
  - el modelo spaCy `es_core_news_lg` para personas, lugares y organizaciones (capa 2).

Después aplica un post-procesado propio:
  - separa «persona» (paciente/familiar) de «sanitario» según el contexto,
  - separa «fecha» genérica de «fecha de nacimiento»,
  - aplica la lista blanca del usuario (términos que nunca se redactan),
  - resuelve solapamientos entre detecciones,
  - añade la frase de contexto y la capa que detectó cada entidad.
"""

import logging
import re
import threading

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

from . import reconocedores_es
from .categorias import CATEGORIAS_POR_ID, IDS_POR_DEFECTO

log = logging.getLogger("anonipro.motor")

# Umbral mínimo de confianza para mostrar una detección
UMBRAL_CONFIANZA = 0.35

# Modelos spaCy por orden de preferencia (el grande si está instalado)
MODELOS_SPACY = ["es_core_news_lg", "es_core_news_md", "es_core_news_sm"]

# Mapa tipo de entidad (Presidio) → id de categoría (categorias.py)
ENTIDAD_A_CATEGORIA = {
    "PERSON": "persona",          # se reclasifica a «sanitario» según contexto
    "SANITARIO": "sanitario",
    "DNI_NIE": "dni_nie",
    "NUSS": "nuss",
    "CIP": "cip",
    "NHC": "nhc",
    "FECHA": "fecha",             # se reclasifica a «fecha_nacimiento» según contexto
    "FECHA_NACIMIENTO": "fecha_nacimiento",
    "SEXO": "sexo",
    "DIRECCION": "direccion",
    "TELEFONO": "telefono",
    "EMAIL": "email",
    "CENTRO": "centro",
    "ORGANIZATION": "centro",     # organizaciones del NER → institucional
    "SERVICIO_UNIDAD": "servicio_unidad",
    "COLEGIADO": "colegiado",
    "LOCALIDAD": "localidad",
    "LOCATION": "localidad",
    "PERSONALIZADA": "personalizada",
}

# Qué entidades hay que pedir al motor para cubrir cada categoría activa.
# (persona y sanitario comparten PERSON; fecha cubre fecha_nacimiento, etc.)
CATEGORIA_A_ENTIDADES = {
    "persona": ["PERSON", "SANITARIO"],
    "sanitario": ["PERSON", "SANITARIO"],
    "dni_nie": ["DNI_NIE"],
    "nuss": ["NUSS"],
    "cip": ["CIP"],
    "nhc": ["NHC"],
    "fecha_nacimiento": ["FECHA", "FECHA_NACIMIENTO"],
    "sexo": ["SEXO"],
    "direccion": ["DIRECCION"],
    "telefono": ["TELEFONO"],
    "email": ["EMAIL"],
    "centro": ["CENTRO", "ORGANIZATION"],
    "servicio_unidad": ["SERVICIO_UNIDAD"],
    "logo": [],  # no viene del texto: se detecta por la estructura del PDF (imágenes)
    "colegiado": ["COLEGIADO"],
    "fecha": ["FECHA", "FECHA_NACIMIENTO"],
    "localidad": ["LOCALIDAD", "LOCATION"],
    "personalizada": ["PERSONALIZADA"],
}

# Contexto que indica que un nombre pertenece a personal sanitario
_RE_CONTEXTO_SANITARIO = re.compile(
    r"(?:dr[a]?\.?|doctor[a]?|fdo\.?|firmado|enf\.?|d\.u\.e\.?|due\b|médic[oa]|facultativ[oa]|"
    r"residente|adjunt[oa]|jefe\s+de\s+servicio|cirujan[oa]|pediatra|enfermer[oa]|matrona|"
    r"colegiad[oa]|atendid[oa]\s+por|valorad[oa]\s+por|firma)\s*:?\s*$",
    re.IGNORECASE,
)

# Contexto que indica que una fecha es de nacimiento
_RE_CONTEXTO_NACIMIENTO = re.compile(
    r"(?:nacimiento|nacid[oa]|f\.?\s*nac\.?|fecha\s+de\s+nac)", re.IGNORECASE
)

# Palabras de plantilla de los informes que el NER confunde con entidades.
# Se comparan tras normalizar (minúsculas, sin puntuación en los bordes).
_RUIDO_NER = {
    "informe", "informe de", "informe de alta", "informe clínico", "informe clinico",
    "teléfono", "telefono", "tfno", "tel", "fax", "correo", "email", "e-mail",
    # verbos frecuentes a inicio de frase que el NER confunde con nombres
    "acude", "refiere", "presenta", "ingresa", "niega", "acudió", "consulta",
    "fdo", "firmado", "dr", "dra", "d", "dña", "dna", "sr", "sra",
    "dni", "nie", "nhc", "cip", "tis", "nuss", "nº col", "no col", "col",
    "domicilio", "dirección", "direccion", "fecha", "fecha de ingreso",
    "fecha de alta", "urgencias", "alta", "ingreso", "paciente", "historia",
    "historia clínica", "historia clinica", "juicio clínico", "juicio clinico",
    "tratamiento", "evolución", "evolucion", "exploración", "exploracion",
    "anamnesis", "antecedentes", "alergias", "constantes", "diagnóstico",
    "diagnostico", "motivo de consulta", "sexo", "edad",
    # títulos profesionales genéricos (no identifican a nadie)
    "médico", "medico", "facultativo", "enfermero", "enfermera", "residente",
    "facultativo de análisis clínicos", "médico peticionario", "atención primaria",
    "medicina interna", "urgencias",
    # analitos de laboratorio que el NER confunde con organizaciones
    "hemoglobina", "leucocitos", "plaquetas", "glucosa", "creatinina", "urea",
    "colesterol", "colesterol total", "trigliceridos", "triglicéridos", "tsh",
    "sodio", "potasio", "hematocrito", "bilirrubina", "got", "gpt", "ggt",
    "ldl", "hdl", "ferritina", "pcr", "vsg", "hba1c",
    # términos anatómicos que empiezan línea con mayúscula en los informes
    # (endoscopias, radiología…) y el NER confunde con nombres o lugares
    "esófago", "esofago", "estómago", "estomago", "duodeno", "yeyuno", "íleon",
    "ileon", "colon", "recto", "ano", "hígado", "higado", "páncreas", "pancreas",
    "vesícula", "vesicula", "bazo", "riñón", "riñones", "rinon", "vejiga",
    "próstata", "prostata", "útero", "utero", "ovario", "ovarios", "mama",
    "mamas", "tiroides", "pulmón", "pulmon", "pulmones", "corazón", "corazon",
    "aorta", "cerebro", "cráneo", "craneo", "columna", "fémur", "femur",
    "húmero", "humero", "rodilla", "hombro", "cadera", "abdomen", "tórax",
    "torax", "pelvis", "cardias", "píloro", "piloro", "bulbo", "mucosa",
    "laringe", "faringe", "tráquea", "traquea", "bronquios", "mediastino",
}


def _recortar_ruido(texto: str, inicio: int, fin: int,
                    extra: set[str] = frozenset()) -> tuple[int, int]:
    """Quita de los bordes de una entidad NER las palabras de plantilla.

    El NER a veces arrastra la etiqueta siguiente («… Tenerife Teléfono») o el
    tratamiento anterior («Dña María…»). Se recortan tokens de los extremos
    mientras estén en la lista de ruido o en `extra` (la lista blanca del
    usuario: así «Esófago» se recorta aunque venga pegado a un nombre).
    """
    tokens = [(m.start() + inicio, m.end() + inicio) for m in re.finditer(r"\S+", texto[inicio:fin])]
    def es_ruido(tok):
        limpio = texto[tok[0]:tok[1]].strip(".:;,–—-ºª()").lower()
        return limpio in _RUIDO_NER or limpio in extra
    while tokens and es_ruido(tokens[-1]):
        tokens.pop()
    while tokens and es_ruido(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return inicio, inicio
    return tokens[0][0], tokens[-1][1]


def _es_ruido_ner(fragmento: str) -> bool:
    """Filtra falsos positivos típicos del NER (palabras de plantilla, códigos)."""
    limpio = fragmento.strip().strip(".:;,–—-ºª ").lower()
    if len(limpio) < 3:
        return True
    if limpio in _RUIDO_NER:
        return True
    # Un «nombre» que es sobre todo dígitos/puntuación no es un nombre
    letras = sum(c.isalpha() for c in limpio)
    return letras < len(limpio) / 2


class MotorDeteccion:
    """Envuelve el AnalyzerEngine de Presidio con la configuración española."""

    def __init__(self):
        self._analyzer: AnalyzerEngine | None = None
        self._lock = threading.Lock()
        self.modelo_cargado: str | None = None

    # ── carga perezosa (el modelo tarda unos segundos en cargar) ──────────
    def _asegurar_cargado(self) -> AnalyzerEngine:
        if self._analyzer is not None:
            return self._analyzer
        with self._lock:
            if self._analyzer is not None:
                return self._analyzer

            modelo = self._elegir_modelo()
            log.info("Cargando modelo NER español: %s", modelo)

            proveedor = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "es", "model_name": modelo}],
                    "ner_model_configuration": {
                        # Mapa de etiquetas del modelo español → entidades Presidio
                        "model_to_presidio_entity_mapping": {
                            "PER": "PERSON",
                            "PERSON": "PERSON",
                            "LOC": "LOCATION",
                            "GPE": "LOCATION",
                            "ORG": "ORGANIZATION",
                        },
                        # MISC del modelo español es demasiado ruidoso
                        "labels_to_ignore": ["MISC", "CARDINAL", "ORDINAL"],
                        "low_confidence_score_multiplier": 0.4,
                        "low_score_entity_names": [],
                    },
                }
            )
            nlp_engine = proveedor.create_engine()

            registro = RecognizerRegistry(supported_languages=["es"])
            # Capa 2: NER de spaCy (personas, lugares, organizaciones)
            registro.add_recognizer(
                SpacyRecognizer(
                    supported_language="es",
                    supported_entities=["PERSON", "LOCATION", "ORGANIZATION"],
                )
            )
            # Capa 1: reglas españolas
            for rec in reconocedores_es.crear_reconocedores_regex():
                registro.add_recognizer(rec)
            for rec in reconocedores_es.crear_reconocedores_contexto():
                registro.add_recognizer(rec)

            self._analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registro,
                supported_languages=["es"],
                default_score_threshold=0.0,  # el umbral se aplica en el post-procesado
            )
            self.modelo_cargado = modelo
            return self._analyzer

    @staticmethod
    def _elegir_modelo() -> str:
        import spacy.util

        for nombre in MODELOS_SPACY:
            if spacy.util.is_package(nombre):
                return nombre
        raise RuntimeError(
            "No hay ningún modelo spaCy en español instalado. "
            "Ejecuta: python -m spacy download es_core_news_lg"
        )

    # ── API principal ──────────────────────────────────────────────────────
    def detectar(
        self,
        texto: str,
        categorias: list[str] | None = None,
        lista_personalizada: list[str] | None = None,
        lista_blanca: list[str] | None = None,
    ) -> list[dict]:
        """Analiza `texto` y devuelve las detecciones como lista de dicts.

        Cada detección: {inicio, fin, texto, categoria, capa, confianza, contexto, detector}
        Los offsets son sobre el texto recibido.
        """
        if not texto or not texto.strip():
            return []

        # Normaliza saltos de línea y tabuladores a espacios (1 carácter → 1
        # carácter, así los offsets no cambian). El NER trabaja mucho mejor
        # con líneas continuas y evita entidades que cruzan renglones.
        texto = texto.replace("\r", " ").replace("\n", " ").replace("\t", " ")

        analyzer = self._asegurar_cargado()
        activas = set(categorias if categorias is not None else IDS_POR_DEFECTO)
        activas = {c for c in activas if c in CATEGORIAS_POR_ID}

        entidades: set[str] = set()
        for cat in activas:
            entidades.update(CATEGORIA_A_ENTIDADES.get(cat, []))

        recs_extra = []
        if "personalizada" in activas and lista_personalizada:
            rec = reconocedores_es.crear_reconocedor_personalizado(lista_personalizada)
            if rec:
                recs_extra.append(rec)

        if not entidades and not recs_extra:
            return []

        resultados = analyzer.analyze(
            text=texto,
            language="es",
            entities=sorted(entidades) if entidades else None,
            ad_hoc_recognizers=recs_extra or None,
            score_threshold=0.0,
        )

        blanca = {t.strip().lower() for t in (lista_blanca or []) if t.strip()}
        # Términos de UNA palabra de la lista blanca: además de respetarse como
        # detección completa, se recortan de los bordes de detecciones mayores
        # (caso real: el NER unió «Nombre Apellidos» + «Esófago» de la línea
        # siguiente en una sola detección).
        blanca_tokens = {t for t in blanca if " " not in t}
        detecciones = []
        for r in resultados:
            fragmento = texto[r.start:r.end]
            categoria = self._clasificar(r.entity_type, texto, r.start, r.end)
            if categoria not in activas:
                continue
            if r.score < UMBRAL_CONFIANZA:
                continue
            nombre_detector = (r.recognition_metadata or {}).get("recognizer_name", "")
            if nombre_detector == "SpacyRecognizer":
                # Recorta palabras de plantilla y de la lista blanca pegadas en
                # los bordes («Santa Cruz de Tenerife Teléfono» → «Santa Cruz de Tenerife»)
                inicio_r, fin_r = _recortar_ruido(texto, r.start, r.end, extra=blanca_tokens)
                if inicio_r >= fin_r:
                    continue
                r.start, r.end = inicio_r, fin_r
                fragmento = texto[r.start:r.end]
                if _es_ruido_ner(fragmento):
                    continue
            # La lista blanca se comprueba DESPUÉS del recorte: si lo que queda
            # coincide con un término respetado, se descarta la detección.
            if fragmento.strip().lower() in blanca:
                continue
            detecciones.append(
                {
                    "inicio": r.start,
                    "fin": r.end,
                    "texto": fragmento,
                    "categoria": categoria,
                    "capa": 2 if nombre_detector == "SpacyRecognizer" else 1,
                    "confianza": round(min(r.score, 1.0), 2),
                    "contexto": self._contexto(texto, r.start, r.end),
                    "detector": nombre_detector,
                }
            )

        return resolver_solapamientos(detecciones, texto)

    # ── post-procesado ─────────────────────────────────────────────────────
    @staticmethod
    def _clasificar(entidad: str, texto: str, inicio: int, fin: int) -> str:
        """Traduce la entidad Presidio a categoría, refinando por contexto."""
        categoria = ENTIDAD_A_CATEGORIA.get(entidad, "persona")

        if entidad == "PERSON":
            previo = texto[max(0, inicio - 40):inicio]
            if _RE_CONTEXTO_SANITARIO.search(previo):
                return "sanitario"
            return "persona"

        if entidad == "FECHA":
            previo = texto[max(0, inicio - 45):inicio]
            if _RE_CONTEXTO_NACIMIENTO.search(previo):
                return "fecha_nacimiento"
            return "fecha"

        return categoria

    @staticmethod
    def _contexto(texto: str, inicio: int, fin: int, radio: int = 70) -> str:
        """Extrae la frase (o fragmento) donde aparece la detección."""
        ini = max(0, inicio - radio)
        fi = min(len(texto), fin + radio)
        fragmento = texto[ini:fi].replace("\n", " ")
        # Recorta a límites de palabra para que se lea bien
        if ini > 0:
            fragmento = "…" + fragmento.split(" ", 1)[-1]
        if fi < len(texto):
            fragmento = fragmento.rsplit(" ", 1)[0] + "…"
        return fragmento.strip()

    @staticmethod
    def _resolver_solapamientos(detecciones: list[dict], texto: str) -> list[dict]:
        return resolver_solapamientos(detecciones, texto)


def resolver_solapamientos(detecciones: list[dict], texto: str) -> list[dict]:
        """Fusiona/filtra detecciones solapadas (capas 1, 2 y 3 juntas).

        - Misma categoría y solapan → se fusionan en un único intervalo.
        - Categorías distintas y solapan → gana la capa de menor número
          (capa 1 validada > capa 2 NER > capa 3 LLM); a igualdad de capa, la de
          mayor confianza y después la más larga. La detección perdedora NO se
          descarta entera: se recorta la parte solapada y se conserva el resto
          (perder texto = riesgo de fuga de datos).
        """
        if not detecciones:
            return []
        detecciones.sort(key=lambda d: (d["inicio"], -d["fin"]))
        resultado: list[dict] = []

        def prioridad(d):
            return (-d["capa"], d["confianza"], d["fin"] - d["inicio"])

        def recortada(d, nuevo_ini, nuevo_fin):
            """Ajusta el intervalo de una detección; None si queda vacía."""
            while nuevo_ini < nuevo_fin and texto[nuevo_ini].isspace():
                nuevo_ini += 1
            while nuevo_fin > nuevo_ini and texto[nuevo_fin - 1].isspace():
                nuevo_fin -= 1
            if nuevo_fin - nuevo_ini < 2:
                return None
            d = dict(d, inicio=nuevo_ini, fin=nuevo_fin, texto=texto[nuevo_ini:nuevo_fin])
            return d

        for d in detecciones:
            if not resultado:
                resultado.append(d)
                continue
            ultimo = resultado[-1]
            if d["inicio"] >= ultimo["fin"]:
                resultado.append(d)
                continue
            # hay solapamiento
            if d["categoria"] == ultimo["categoria"]:
                ultimo["fin"] = max(ultimo["fin"], d["fin"])
                ultimo["texto"] = texto[ultimo["inicio"]:ultimo["fin"]]
                ultimo["confianza"] = max(ultimo["confianza"], d["confianza"])
                ultimo["capa"] = min(ultimo["capa"], d["capa"])
            elif prioridad(d) > prioridad(ultimo):
                # `d` gana: recorta el final de `ultimo` y añade `d`
                previa = recortada(ultimo, ultimo["inicio"], d["inicio"])
                if previa is not None:
                    resultado[-1] = previa
                    resultado.append(d)
                else:
                    resultado[-1] = d
            else:
                # `ultimo` gana: conserva de `d` solo lo que sobresale
                resto = recortada(d, ultimo["fin"], d["fin"])
                if resto is not None:
                    resultado.append(resto)
        return resultado


# Instancia única compartida por toda la aplicación
MOTOR = MotorDeteccion()
