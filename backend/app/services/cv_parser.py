"""Análisis automático de CV en PDF o Word.

1. Extracción de texto: pdfplumber (PDF) o python-docx (DOCX, incluye tablas).
2. Segmentación por secciones (experiencia, educación, habilidades...) usando
   encabezados típicos de CV en español e inglés.
3. Entidades: spaCy `es_core_news_sm` para el nombre (PER) y organizaciones (ORG);
   expresiones regulares para correo, teléfono y LinkedIn.
4. Experiencia: rangos de fechas ("ene 2019 – actualidad") convertidos a meses,
   fusionando periodos solapados para no contar dos veces trabajos simultáneos.

Si el modelo de spaCy no está instalado se usa un motor de reglas, de modo que la
postulación nunca falla por el análisis.
"""
import io
import logging
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.services.habilidades import normalizar

log = logging.getLogger(__name__)

EXTENSIONES = {".pdf": "application/pdf",
               ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


class CVInvalido(ValueError):
    pass


# ---------------------------------------------------------------- texto ---

def validar_archivo(nombre: str, contenido: bytes) -> str:
    """Valida extensión, tamaño y firma binaria. Devuelve el MIME."""
    ext = Path(nombre).suffix.lower()
    if ext == ".doc":
        raise CVInvalido("El formato .doc (Word 97-2003) no es compatible. Guarda el archivo como .docx o PDF.")
    if ext not in EXTENSIONES:
        raise CVInvalido("Solo se aceptan CV en PDF o Word (.docx).")
    if len(contenido) > settings.max_cv_mb * 1024 * 1024:
        raise CVInvalido(f"El archivo supera el máximo de {settings.max_cv_mb} MB.")
    # No confiar en la extensión: un .pdf debe empezar por %PDF y un .docx es un ZIP.
    firma_ok = contenido.startswith(b"%PDF") if ext == ".pdf" else contenido.startswith(b"PK\x03\x04")
    if not firma_ok:
        raise CVInvalido("El contenido del archivo no corresponde a su extensión.")
    return EXTENSIONES[ext]


def extraer_texto(nombre: str, contenido: bytes) -> str:
    ext = Path(nombre).suffix.lower()
    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(io.BytesIO(contenido)) as pdf:
                paginas = [p.extract_text() or "" for p in pdf.pages[:15]]
            return "\n".join(paginas).strip()
        import docx
        documento = docx.Document(io.BytesIO(contenido))
        lineas = [p.text for p in documento.paragraphs]
        for tabla in documento.tables:  # muchos CV maquetan en tablas
            for fila in tabla.rows:
                celdas = []
                for c in fila.cells:
                    if c.text.strip() and c.text.strip() not in celdas:
                        celdas.append(c.text.strip())
                lineas.extend(celdas)
        return "\n".join(lineas).strip()
    except Exception as exc:  # archivo corrupto o protegido
        log.warning("No se pudo leer el CV %s: %s", nombre, exc)
        raise CVInvalido("No se pudo leer el archivo. ¿Está protegido con contraseña o dañado?") from exc


# ------------------------------------------------------------ secciones ---

_SECCIONES = {
    "perfil": r"perfil|resumen|sobre mi|acerca de mi|objetivo|summary|profile",
    "experiencia": r"experiencia|historial laboral|trayectoria|work experience|experience|employment",
    "educacion": r"educacion|formacion|estudios|education|academic",
    "habilidades": r"habilidades|competencias|conocimientos|tecnologias|herramientas|skills|stack",
    "idiomas": r"idiomas|languages",
    "certificaciones": r"certificaciones|certificados|cursos|certifications",
    "proyectos": r"proyectos|projects|portafolio",
    "referencias": r"referencias|references",
}
_ENCABEZADO = re.compile(
    r"^(?P<sec>" + "|".join(f"(?P<{k}>{v})" for k, v in _SECCIONES.items()) + r")\b[\w\s]{0,25}:?$"
)


def segmentar(texto: str) -> dict[str, list[str]]:
    secciones: dict[str, list[str]] = {"encabezado": []}
    actual = "encabezado"
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia:
            continue
        m = _ENCABEZADO.match(normalizar(limpia).strip(" :-•·|"))
        if m and len(limpia) <= 45:
            actual = next(k for k in _SECCIONES if m.group(k))
            secciones.setdefault(actual, [])
            continue
        secciones.setdefault(actual, []).append(limpia)
    return secciones


# --------------------------------------------------------------- fechas ---

_MESES = {
    "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "aug": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12, "dec": 12,
}
_MES = r"(?:(?P<{n}m>ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic|jan|apr|aug|dec)[a-z]*\.?\s*(?:de\s+)?|(?P<{n}n>\d{{1,2}})[/.-])?"
_RANGO = re.compile(
    _MES.format(n="d") + r"(?P<da>(?:19|20)\d{2})\s*(?:-|–|—|a|al|hasta|to)\s*"
    r"(?:" + _MES.format(n="h") + r"(?P<ha>(?:19|20)\d{2})|(?P<hoy>actualidad|actual|presente|la fecha|hoy|present|current|now))"
)


def _mes(m: re.Match, prefijo: str, por_defecto: int) -> int:
    if m.group(f"{prefijo}m"):
        return _MESES[m.group(f"{prefijo}m")[:3]]
    if m.group(f"{prefijo}n") and 1 <= int(m.group(f"{prefijo}n")) <= 12:
        return int(m.group(f"{prefijo}n"))
    return por_defecto


def rangos_de_fechas(texto: str, hoy: date | None = None) -> list[tuple[int, int, str]]:
    """Lista de (mes_inicio, mes_fin, texto) expresados como año*12+mes."""
    hoy = hoy or date.today()
    rangos = []
    for m in _RANGO.finditer(normalizar(texto)):
        inicio = int(m.group("da")) * 12 + _mes(m, "d", 1)
        if m.group("hoy"):
            fin = hoy.year * 12 + hoy.month
        else:
            fin = int(m.group("ha")) * 12 + _mes(m, "h", 12)
        if inicio <= fin <= hoy.year * 12 + hoy.month:
            rangos.append((inicio, fin, m.group(0)))
    return rangos


def anios_de_experiencia(rangos: list[tuple[int, int, str]]) -> float:
    """Suma de meses fusionando solapamientos, redondeada a medio año."""
    meses = 0
    fin_actual = None
    inicio_actual = None
    for inicio, fin, _ in sorted(rangos):
        if fin_actual is None or inicio > fin_actual:
            if fin_actual is not None:
                meses += fin_actual - inicio_actual
            inicio_actual, fin_actual = inicio, fin
        else:
            fin_actual = max(fin_actual, fin)
    if fin_actual is not None:
        meses += fin_actual - inicio_actual
    return round(meses / 12 * 2) / 2


# ------------------------------------------------------------ entidades ---

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TELEFONO = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}")
_LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.I)
_TITULOS = re.compile(
    r"\b(universidad|instituto|colegio|escuela|licenciad|ingenier|maestr|master|mba|doctor|bachiller|"
    r"tecnico|tecnologo|t\.?s\.?u|diplomado|bootcamp|grado|degree|university|bachelor)", re.I
)


@lru_cache(maxsize=1)
def _nlp():
    try:
        import spacy
        return spacy.load(settings.spacy_modelo, disable=["lemmatizer"])
    except Exception as exc:
        log.warning("spaCy no disponible (%s); se usará el motor de reglas.", exc)
        return None


def _parece_nombre(texto: str) -> bool:
    palabras = texto.split()
    return (2 <= len(palabras) <= 5 and not any(ch.isdigit() for ch in texto)
            and "@" not in texto and all(p[0].isupper() for p in palabras if len(p) > 3))


def _detectar_nombre(encabezado: list[str], nlp) -> str | None:
    if nlp is not None:
        for linea in encabezado[:6]:
            for ent in nlp(linea).ents:
                if ent.label_ == "PER" and _parece_nombre(ent.text.strip()):
                    return ent.text.strip().title() if ent.text.isupper() else ent.text.strip()
    for linea in encabezado[:4]:
        if _parece_nombre(linea):
            return linea.title() if linea.isupper() else linea
    return None


# ------------------------------------------------------------- análisis ---

def analizar(texto: str, hoy: date | None = None) -> dict:
    secciones = segmentar(texto)
    nlp = _nlp()

    email = _EMAIL.search(texto)
    linkedin = _LINKEDIN.search(texto)
    telefono = None
    for m in _TELEFONO.finditer(texto):
        digitos = re.sub(r"\D", "", m.group(0))
        if 7 <= len(digitos) <= 15 and not re.fullmatch(r"(19|20)\d{2}(19|20)\d{2}", digitos):
            telefono = m.group(0).strip()
            break

    # Experiencia: preferir la sección; si el CV no tiene encabezados, usar todo el texto.
    lineas_exp = secciones.get("experiencia") or [l for l in texto.splitlines() if l.strip()]
    rangos = rangos_de_fechas("\n".join(lineas_exp), hoy)
    experiencia = []
    for i, linea in enumerate(lineas_exp):
        encontrados = rangos_de_fechas(linea, hoy)
        if not encontrados:
            continue
        titulo = re.sub(r"[|,·•()\-–—\s]+$", "", _RANGO.sub("", normalizar(linea))).strip()
        titulo = linea if len(titulo) > 3 else (lineas_exp[i - 1] if i > 0 else linea)
        inicio, fin, periodo = encontrados[0]
        experiencia.append({"puesto": titulo[:160], "periodo": periodo, "meses": fin - inicio})

    educacion = secciones.get("educacion") or [l for l in texto.splitlines() if _TITULOS.search(normalizar(l))]
    organizaciones: list[str] = []
    if nlp is not None and lineas_exp:
        for ent in nlp("\n".join(lineas_exp)[:5000]).ents:
            if ent.label_ == "ORG" and ent.text.strip() not in organizaciones and len(ent.text) > 2:
                organizaciones.append(ent.text.strip())

    return {
        "motor": "spacy" if nlp is not None else "reglas",
        "nombre": _detectar_nombre(secciones.get("encabezado", []), nlp),
        "email": email.group(0).lower() if email else None,
        "telefono": telefono,
        "linkedin": linkedin.group(0) if linkedin else None,
        "perfil": " ".join(secciones.get("perfil", []))[:800] or None,
        "experiencia": experiencia[:12],
        "experiencia_anios": anios_de_experiencia(rangos),
        "educacion": [e[:200] for e in educacion[:8]],
        "idiomas": secciones.get("idiomas", [])[:6],
        "organizaciones": organizaciones[:10],
        "secciones": [s for s in secciones if s != "encabezado"],
    }
