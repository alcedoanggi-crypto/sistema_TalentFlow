"""Modo "uso personal": mi propia búsqueda de empleo.

Registro las vacantes a las que me postulo, su estado, fechas de seguimiento y
recordatorios, y comparo MI CV contra la descripción de cada vacante usando el
mismo motor de habilidades y match que usa el ATS con los candidatos.
"""
import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_actual
from app.models import MiCV, MiPostulacion, MiRecordatorio, Usuario
from app.schemas import MiPostulacionIn, RecordatorioIn
from app.services.cv_parser import CVInvalido
from app.services.habilidades import detectar_habilidades, normalizar
from app.services.matching import Requisito, calcular_match
from app.services.postulaciones import procesar_cv

router = APIRouter(prefix="/api/personal", tags=["uso personal"])

_DESEABLE = re.compile(r"deseable|valorable|plus|nice to have|se valora|preferible|opcional|bonus|ideal")
_ANIOS = re.compile(r"(\d{1,2})\s*\+?\s*(?:anos|years|yrs)")


def analizar_descripcion(db: Session, texto: str) -> tuple[list[Requisito], float]:
    """Extrae requisitos de una oferta pegada como texto libre.

    Una habilidad es "deseable" si aparece en una línea/frase con palabras como
    "deseable", "plus" o "nice to have" (o bajo un encabezado así); si no, es obligatoria.
    """
    requisitos: dict[int, Requisito] = {}
    en_bloque_deseable = False
    for linea in re.split(r"[\n;]|(?<=\.)\s", texto or ""):
        norm = normalizar(linea)
        if not norm:
            continue
        es_encabezado = len(norm) < 40 and norm.rstrip(":").strip() and norm.endswith(":")
        if es_encabezado:
            en_bloque_deseable = bool(_DESEABLE.search(norm))
        tipo = "deseable" if (en_bloque_deseable or _DESEABLE.search(norm)) else "obligatoria"
        for hid, nombre in detectar_habilidades(db, linea).items():
            if hid not in requisitos or tipo == "obligatoria":
                requisitos[hid] = Requisito(hid, nombre, tipo)
    anios = [int(m.group(1)) for m in _ANIOS.finditer(normalizar(texto or "")) if int(m.group(1)) <= 25]
    return list(requisitos.values()), float(max(anios) if anios else 0)


def _mi_cv(db: Session, u: Usuario) -> MiCV | None:
    return db.get(MiCV, u.id)


def _analizar(db: Session, mp: MiPostulacion, cv: MiCV | None) -> None:
    if cv is None or not mp.descripcion:
        mp.match_score, mp.match_detalle = None, None
        return
    requisitos, anios = analizar_descripcion(db, mp.descripcion)
    mias = detectar_habilidades(db, cv.texto)
    detalle = calcular_match(mias, float(cv.datos.get("experiencia_anios") or 0), requisitos, anios)
    # Consejo accionable: qué aprender primero (las obligatorias faltantes pesan más).
    detalle["sugerencias"] = (
        [f"Refuerza o menciona explícitamente «{h}» en tu CV: es un requisito obligatorio." for h in detalle["obligatorias"]["faltan"]]
        + [f"«{h}» suma puntos como deseable." for h in detalle["deseables"]["faltan"][:3]])
    if not requisitos:
        detalle["sugerencias"].insert(0, "No se detectaron habilidades conocidas en la descripción. "
                                         "Pega el texto completo de la oferta o agrega las habilidades al catálogo.")
    mp.match_score, mp.match_detalle = detalle["score"], detalle


def _dict(mp: MiPostulacion) -> dict:
    hoy = date.today()
    return {
        "id": mp.id, "empresa": mp.empresa, "puesto": mp.puesto, "url": mp.url, "descripcion": mp.descripcion,
        "modalidad": mp.modalidad, "salario": mp.salario, "estado": mp.estado, "contacto": mp.contacto,
        "notas": mp.notas, "fecha_postulacion": mp.fecha_postulacion.isoformat() if mp.fecha_postulacion else None,
        "proximo_seguimiento": mp.proximo_seguimiento.isoformat() if mp.proximo_seguimiento else None,
        "seguimiento_vencido": bool(mp.proximo_seguimiento and mp.proximo_seguimiento < hoy
                                    and mp.estado not in ("aceptada", "rechazada")),
        "match_score": float(mp.match_score) if mp.match_score is not None else None,
        "match_detalle": mp.match_detalle,
        "recordatorios": [{"id": r.id, "fecha": r.fecha.isoformat(), "texto": r.texto, "completado": r.completado}
                          for r in mp.recordatorios],
        "actualizada_en": mp.actualizada_en.isoformat() if mp.actualizada_en else None,
    }


def _mia(db: Session, mid: int, u: Usuario) -> MiPostulacion:
    mp = db.get(MiPostulacion, mid)
    if mp is None or mp.usuario_id != u.id:
        raise HTTPException(404, "Registro no encontrado")
    return mp


@router.get("/cv")
def ver_cv(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    cv = _mi_cv(db, u)
    return None if cv is None else {"nombre_original": cv.nombre_original, "datos": cv.datos,
                                    "actualizado_en": cv.actualizado_en.isoformat(), "caracteres": len(cv.texto)}


@router.put("/cv")
async def subir_cv(archivo: UploadFile = File(...), u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    contenido = await archivo.read()
    try:
        _, texto, datos, _ = procesar_cv(db, archivo.filename or "cv.pdf", contenido)
    except CVInvalido as exc:
        raise HTTPException(400, str(exc))
    cv = _mi_cv(db, u) or MiCV(usuario_id=u.id)
    cv.nombre_original, cv.texto, cv.datos = archivo.filename, texto, datos
    db.merge(cv)
    db.flush()
    cv = _mi_cv(db, u)
    for mp in db.scalars(select(MiPostulacion).where(MiPostulacion.usuario_id == u.id)):
        _analizar(db, mp, cv)   # el CV cambió: se recalcula el match de todas mis vacantes
    db.commit()
    return ver_cv(u, db)


@router.get("/postulaciones")
def listar(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    filas = db.scalars(select(MiPostulacion).where(MiPostulacion.usuario_id == u.id)
                       .order_by(MiPostulacion.actualizada_en.desc())).all()
    hoy = date.today()
    pendientes = db.execute(
        select(MiRecordatorio, MiPostulacion).join(MiPostulacion)
        .where(MiPostulacion.usuario_id == u.id, MiRecordatorio.completado.is_(False),
               MiRecordatorio.fecha <= hoy + timedelta(days=7)).order_by(MiRecordatorio.fecha)).all()
    por_estado: dict[str, int] = {}
    for mp in filas:
        por_estado[mp.estado] = por_estado.get(mp.estado, 0) + 1
    enviadas = [mp for mp in filas if mp.estado != "por_postular"]
    con_respuesta = [mp for mp in enviadas if mp.estado not in ("postulada", "sin_respuesta")]
    scores = [float(mp.match_score) for mp in filas if mp.match_score is not None]
    # Habilidades que más me faltan en todas las vacantes: guía de qué estudiar.
    faltantes: dict[str, int] = {}
    for mp in filas:
        for h in (mp.match_detalle or {}).get("obligatorias", {}).get("faltan", []):
            faltantes[h] = faltantes.get(h, 0) + 1
    return {
        "postulaciones": [_dict(mp) for mp in filas],
        "resumen": {"total": len(filas), "por_estado": por_estado,
                    "tasa_respuesta": round(len(con_respuesta) / len(enviadas) * 100, 1) if enviadas else 0,
                    "match_promedio": round(sum(scores) / len(scores), 1) if scores else None,
                    "habilidades_a_reforzar": sorted(faltantes.items(), key=lambda kv: -kv[1])[:8]},
        "recordatorios": [{"id": r.id, "fecha": r.fecha.isoformat(), "texto": r.texto, "postulacion_id": mp.id,
                           "empresa": mp.empresa, "puesto": mp.puesto, "vencido": r.fecha < hoy}
                          for r, mp in pendientes],
    }


@router.post("/postulaciones", status_code=201)
def crear(datos: MiPostulacionIn, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    mp = MiPostulacion(usuario_id=u.id, **datos.model_dump())
    if mp.estado != "por_postular" and mp.fecha_postulacion is None:
        mp.fecha_postulacion = date.today()
    if mp.fecha_postulacion and mp.proximo_seguimiento is None:
        mp.proximo_seguimiento = mp.fecha_postulacion + timedelta(days=7)   # regla: dar seguimiento a la semana
    _analizar(db, mp, _mi_cv(db, u))
    db.add(mp)
    db.flush()
    if mp.proximo_seguimiento:
        mp.recordatorios.append(MiRecordatorio(fecha=mp.proximo_seguimiento,
                                               texto=f"Dar seguimiento a {mp.empresa} ({mp.puesto})"))
    db.commit()
    db.refresh(mp)
    return _dict(mp)


@router.put("/postulaciones/{mid}")
def editar(mid: int, datos: MiPostulacionIn, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    mp = _mia(db, mid, u)
    cambio_desc = datos.descripcion != mp.descripcion
    for k, v in datos.model_dump().items():
        setattr(mp, k, v)
    if mp.estado != "por_postular" and mp.fecha_postulacion is None:
        mp.fecha_postulacion = date.today()
    if cambio_desc or mp.match_score is None:
        _analizar(db, mp, _mi_cv(db, u))
    db.commit()
    db.refresh(mp)
    return _dict(mp)


@router.post("/postulaciones/{mid}/analizar")
def reanalizar(mid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    mp = _mia(db, mid, u)
    cv = _mi_cv(db, u)
    if cv is None:
        raise HTTPException(400, "Primero sube tu CV en «Mi CV».")
    _analizar(db, mp, cv)
    db.commit()
    return _dict(mp)


@router.delete("/postulaciones/{mid}", status_code=204)
def borrar(mid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    db.delete(_mia(db, mid, u))
    db.commit()


@router.post("/postulaciones/{mid}/recordatorios", status_code=201)
def agregar_recordatorio(mid: int, datos: RecordatorioIn, u: Usuario = Depends(usuario_actual),
                         db: Session = Depends(get_db)):
    mp = _mia(db, mid, u)
    mp.recordatorios.append(MiRecordatorio(**datos.model_dump()))
    db.commit()
    db.refresh(mp)
    return _dict(mp)


@router.patch("/recordatorios/{rid}")
def actualizar_recordatorio(rid: int, datos: dict, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    r = db.get(MiRecordatorio, rid)
    if r is None or _mia(db, r.mi_postulacion_id, u) is None:
        raise HTTPException(404, "Recordatorio no encontrado")
    if "completado" in datos:
        r.completado = bool(datos["completado"])
    db.commit()
    return {"ok": True}


@router.delete("/recordatorios/{rid}", status_code=204)
def borrar_recordatorio(rid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    r = db.get(MiRecordatorio, rid)
    if r is not None and _mia(db, r.mi_postulacion_id, u):
        db.delete(r)
        db.commit()
