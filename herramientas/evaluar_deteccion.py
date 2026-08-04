"""Métricas de detección por categoría sobre un corpus sintético (Fase 4).

Genera N documentos clínicos sintéticos donde CADA dato personal insertado queda
registrado como «verdad terreno» (sabemos qué hay y de qué categoría es), pasa el
motor de detección (capas 1-2) y calcula por categoría:

  - Sensibilidad (exhaustividad): de los datos reales, ¿cuántos se detectaron?
  - Precisión (VPP): de lo detectado, ¿cuánto era realmente un dato?

Nota metodológica honesta: en detección de entidades no se puede calcular la
«especificidad» clásica (no existe un número finito de verdaderos negativos),
así que se informa la precisión, que es el equivalente útil: mide los falsos
positivos. Un dato cuenta como detectado si algún resaltado de su misma
categoría lo cubre (coincidencia por texto normalizado).

Uso (desde la raíz del proyecto):
    .venv/bin/python herramientas/evaluar_deteccion.py [n_documentos]
"""

import random
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.detection.motor import MOTOR  # noqa: E402

random.seed(2026)  # reproducible

# ── bancos de datos sintéticos ─────────────────────────────────────────────
NOMBRES = ["María", "José", "Carmen", "Antonio", "Lucía", "Manuel", "Ana", "Francisco",
           "Elena", "David", "Pino", "Airam", "Yeray", "Idaira", "Nayra", "Jonay"]
APELLIDOS = ["Pérez", "Rodríguez", "García", "Hernández", "Betancor", "Cabrera",
             "Marrero", "Santana", "Déniz", "Padrón", "Quintana", "Armas", "Toledo", "Sosa"]
CALLES = ["C/ La Marina 12", "Avda. de Anaga 45, 3ºB", "Calle El Pilar 8",
          "Ctra. General del Norte 102", "Plaza del Adelantado 3", "Camino Largo 21"]
LOCALIDADES = ["Santa Cruz de Tenerife", "La Laguna", "Las Palmas de Gran Canaria",
               "Arrecife", "Puerto del Rosario", "Los Llanos de Aridane", "Telde", "Adeje"]
CENTROS = ["Hospital Universitario Nuestra Señora de la Candelaria",
           "Hospital Universitario de Canarias", "Hospital General de La Palma",
           "Centro de Salud de Taco", "Hospital Universitario Insular de Gran Canaria"]
SERVICIOS = ["Servicio de Pediatría", "Servicio de Medicina Interna", "Unidad de Cardiología",
             "Servicio de Digestivo", "Unidad de Cuidados Intensivos", "Sección de Neurología"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni():
    n = random.randint(10_000_000, 79_999_999)
    return f"{n}{LETRAS_DNI[n % 23]}"


def nuss():
    prov, sec = random.choice([35, 38]), random.randint(10_000_000, 99_999_999)
    return f"{prov} {sec} {int(f'{prov}{sec}') % 97:02d}"


def cip_sns():
    return "BBBBBBBB" + "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2)) + \
        f"{random.randint(0, 999999):06d}"


def telefono():
    pref = random.choice(["6", "7", "822", "928", "922"])
    resto = "".join(random.choices("0123456789", k=9 - len(pref)))
    t = pref + resto
    return f"{t[:3]} {t[3:5]} {t[5:7]} {t[7:]}"


def fecha_numerica():
    return f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1990, 2025)}"


def fecha_textual():
    return f"{random.randint(1, 28)} de {random.choice(MESES)} de {random.randint(2020, 2025)}"


def nombre_completo():
    return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"


def colegiado():
    return f"38/38/{random.randint(1000, 99999):05d}"


# ── plantilla de documento con verdad terreno ──────────────────────────────
def generar_documento() -> tuple[str, list[tuple[str, str]]]:
    """Devuelve (texto, verdad_terreno) con verdad_terreno = [(categoria, texto)]."""
    gt: list[tuple[str, str]] = []

    def pon(categoria, valor):
        gt.append((categoria, valor))
        return valor

    paciente = pon("persona", nombre_completo())
    familiar = pon("persona", nombre_completo())
    medico = pon("sanitario", nombre_completo())
    centro = pon("centro", random.choice(CENTROS))
    servicio = pon("servicio_unidad", random.choice(SERVICIOS))
    v_dni = pon("dni_nie", dni())
    v_nuss = pon("nuss", nuss())
    v_cip = pon("cip", cip_sns())
    v_nhc = pon("nhc", str(random.randint(100000, 999999)))
    v_fnac = pon("fecha_nacimiento", fecha_numerica())
    v_tel = pon("telefono", telefono())
    usuario_mail = f"{paciente.split()[0].lower()}.{random.randint(1, 99)}@correo.es"
    v_mail = pon("email", unicodedata.normalize("NFD", usuario_mail).encode("ascii", "ignore").decode())
    v_dir = pon("direccion", random.choice(CALLES))
    v_loc = pon("localidad", random.choice(LOCALIDADES))
    v_f1 = pon("fecha", fecha_textual())
    v_f2 = pon("fecha", fecha_numerica())
    v_col = pon("colegiado", colegiado())

    texto = f"""INFORME CLÍNICO
{centro}
{servicio}

Paciente: {paciente}
DNI: {v_dni}  NHC: {v_nhc}  CIP: {v_cip}
NUSS: {v_nuss}
F. Nac.: {v_fnac}
Domicilio: {v_dir}, {v_loc}
Teléfono: {v_tel}  Correo: {v_mail}

Motivo de consulta: dolor abdominal de dos días de evolución.
Acude el {v_f1} en compañía de su familiar, D. {familiar}.
Exploración dentro de la normalidad. Analítica sin hallazgos relevantes.
Juicio clínico: proceso intercurrente banal. Control con su equipo habitual.
Próxima revisión: {v_f2}.

Fdo.: Dra. {medico}. Nº Col.: {v_col}
"""
    return texto, gt


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def evaluar(n_docs: int = 40):
    tp: dict[str, int] = {}    # datos reales detectados
    fn: dict[str, int] = {}    # datos reales NO detectados
    det_ok: dict[str, int] = {}    # detecciones que corresponden a un dato real
    det_fp: dict[str, int] = {}    # detecciones sin dato real detrás (falsos positivos)
    ejemplos_fn: dict[str, list] = {}

    for _ in range(n_docs):
        texto, gt = generar_documento()
        detecciones = MOTOR.detectar(texto)

        # sensibilidad: cada dato real ¿está cubierto por una detección de su categoría?
        for categoria, valor in gt:
            cubierto = any(
                d["categoria"] == categoria and
                (_norm(valor) in _norm(d["texto"]) or _norm(d["texto"]) in _norm(valor))
                for d in detecciones
            )
            if cubierto:
                tp[categoria] = tp.get(categoria, 0) + 1
            else:
                fn[categoria] = fn.get(categoria, 0) + 1
                ejemplos_fn.setdefault(categoria, []).append(valor)

        # precisión: cada detección ¿corresponde a algún dato real?
        for d in detecciones:
            corresponde = any(
                (_norm(v) in _norm(d["texto"]) or _norm(d["texto"]) in _norm(v))
                for c, v in gt if c == d["categoria"]
            )
            clave = d["categoria"]
            if corresponde:
                det_ok[clave] = det_ok.get(clave, 0) + 1
            else:
                det_fp[clave] = det_fp.get(clave, 0) + 1

    categorias = sorted(set(tp) | set(fn) | set(det_ok) | set(det_fp))
    print(f"\nEvaluación sobre {n_docs} documentos sintéticos (capas 1-2, sin LLM)")
    print(f"{'Categoría':18} {'Sensibilidad':>13} {'Precisión':>11}   (reales, detecciones)")
    print("-" * 66)
    tot_tp = tot_fn = tot_ok = tot_fp = 0
    for c in categorias:
        vp, f = tp.get(c, 0), fn.get(c, 0)
        ok, fp = det_ok.get(c, 0), det_fp.get(c, 0)
        tot_tp += vp; tot_fn += f; tot_ok += ok; tot_fp += fp
        sens = vp / (vp + f) if vp + f else float("nan")
        prec = ok / (ok + fp) if ok + fp else float("nan")
        print(f"{c:18} {sens:12.1%} {prec:10.1%}   ({vp + f}, {ok + fp})")
    print("-" * 66)
    sens_g = tot_tp / (tot_tp + tot_fn)
    prec_g = tot_ok / (tot_ok + tot_fp)
    print(f"{'GLOBAL':18} {sens_g:12.1%} {prec_g:10.1%}   ({tot_tp + tot_fn}, {tot_ok + tot_fp})")

    fallados = {c: v[:3] for c, v in ejemplos_fn.items() if v}
    if fallados:
        print("\nEjemplos de datos NO detectados (para mejorar el motor):")
        for c, ejemplos in fallados.items():
            print(f"  {c}: {ejemplos}")
    print("\nNota: la «especificidad» clásica no es calculable en detección de entidades")
    print("(no hay un nº finito de verdaderos negativos); la precisión cumple ese papel.")


if __name__ == "__main__":
    evaluar(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
