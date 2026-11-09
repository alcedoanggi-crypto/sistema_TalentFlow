"""Normalización de habilidades y detección en texto libre.

La tabla habilidad_sinonimos guarda cada forma conocida ("js", "javascript",
"ecmascript") apuntando a una habilidad canónica ("JavaScript"). Para detectar
habilidades en un CV se compila una sola expresión regular con todos los
sinónimos, ordenados del más largo al más corto para que "react native" gane a
"react" y "node.js" a "node".
"""
import re
import unicodedata
from dataclasses import dataclass
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Habilidad, HabilidadSinonimo


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios colapsados: 'Programación  JS' -> 'programacion js'."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


@dataclass(frozen=True)
class _Indice:
    patron: re.Pattern | None
    por_sinonimo: dict[str, tuple[int, str]]   # sinonimo -> (habilidad_id, nombre canónico)


_indice: _Indice | None = None
_lock = Lock()


def invalidar_indice() -> None:
    """Llamar después de crear o editar habilidades/sinónimos."""
    global _indice
    with _lock:
        _indice = None


def _construir_indice(db: Session) -> _Indice:
    filas = db.execute(
        select(HabilidadSinonimo.sinonimo, Habilidad.id, Habilidad.nombre)
        .join(Habilidad, Habilidad.id == HabilidadSinonimo.habilidad_id)
    ).all()
    por_sinonimo: dict[str, tuple[int, str]] = {}
    for sinonimo, hid, nombre in filas:
        por_sinonimo[normalizar(sinonimo)] = (hid, nombre)
    # El nombre canónico siempre cuenta como sinónimo de sí mismo.
    for hid, nombre in db.execute(select(Habilidad.id, Habilidad.nombre)).all():
        por_sinonimo.setdefault(normalizar(nombre), (hid, nombre))

    if not por_sinonimo:
        return _Indice(None, {})
    alternativas = "|".join(re.escape(s) for s in sorted(por_sinonimo, key=len, reverse=True))
    # Límites "de palabra" que entienden símbolos técnicos: C++, C#, .NET, Node.js.
    patron = re.compile(rf"(?<![a-z0-9+#])(?:{alternativas})(?![a-z0-9+#]|\.[a-z0-9])")
    return _Indice(patron, por_sinonimo)


def _obtener_indice(db: Session) -> _Indice:
    global _indice
    with _lock:
        if _indice is None:
            _indice = _construir_indice(db)
        return _indice


def detectar_habilidades(db: Session, texto: str) -> dict[int, str]:
    """Devuelve {habilidad_id: nombre canónico} de todas las habilidades mencionadas."""
    indice = _obtener_indice(db)
    if not texto or indice.patron is None:
        return {}
    encontradas: dict[int, str] = {}
    for m in indice.patron.finditer(normalizar(texto)):
        hid, nombre = indice.por_sinonimo[m.group(0)]
        encontradas[hid] = nombre
    return encontradas


def terminos_detectados(db: Session, texto: str) -> dict[str, str]:
    """{forma normalizada encontrada en el texto: nombre canónico}. La interfaz lo usa para
    resaltar en el CV exactamente las palabras que generaron cada habilidad ("Postgres" → PostgreSQL)."""
    indice = _obtener_indice(db)
    if not texto or indice.patron is None:
        return {}
    return {m.group(0): indice.por_sinonimo[m.group(0)][1] for m in indice.patron.finditer(normalizar(texto))}


def resolver(db: Session, termino: str) -> Habilidad | None:
    """Resuelve un término cualquiera ('Postgres') a su habilidad canónica ('PostgreSQL')."""
    indice = _obtener_indice(db)
    encontrado = indice.por_sinonimo.get(normalizar(termino))
    return db.get(Habilidad, encontrado[0]) if encontrado else None
