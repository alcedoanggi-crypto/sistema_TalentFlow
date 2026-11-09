from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import Session

from app import serializers
from app.config import settings
from app.database import get_db
from app.deps import GESTION, obtener, requiere, usuario_actual
from app.models import (
    Candidato, CandidatoHabilidad, Correo, Documento, Entrevista, Postulacion, PruebaAsignacion, Usuario, Vacante,
)
from app.schemas import MoverIn
from app.services import privacidad
from app.services.habilidades import resolver, terminos_detectados
from app.services.postulaciones import ErrorNegocio, mover_etapa, recalcular_match

router = APIRouter(prefix="/api", tags=["candidatos"])


def _de_empresa(empresa_id: int):
    """Candidatos con al menos una postulación a vacantes de la empresa."""
    return exists().where(Postulacion.candidato_id == Candidato.id, Postulacion.vacante_id == Vacante.id,
                          Vacante.empresa_id == empresa_id)


def _candidato(db: Session, cid: int, u: Usuario) -> Candidato:
    c = db.get(Candidato, cid)
    if c is None or not db.scalar(select(_de_empresa(u.empresa_id)).where(Candidato.id == cid)):
        raise HTTPException(404, "Candidato no encontrado")
    return c


def postulacion_de(db: Session, pid: int, u: Usuario) -> Postulacion:
    p = db.get(Postulacion, pid)
    if p is None or p.vacante.empresa_id != u.empresa_id:
        raise HTTPException(404, "Postulación no encontrada")
    return p


@router.get("/candidatos")
def buscar(q: str | None = None, habilidad: list[str] | None = Query(None), limite: int = 50,
           u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Búsqueda full-text sobre el contenido de los CV (índice GIN sobre documentos.tsv).

    `q` acepta sintaxis tipo buscador: `"análisis de datos" python -java`.
    """
    base = (select(Candidato).where(_de_empresa(u.empresa_id), Candidato.anonimizado_en.is_(None)))
    for termino in habilidad or []:
        h = resolver(db, termino)
        if h is None:
            return []
        base = base.where(exists().where(CandidatoHabilidad.candidato_id == Candidato.id,
                                         CandidatoHabilidad.habilidad_id == h.id))
    if not q:
        filas = [(c, None, None) for c in db.scalars(base.order_by(Candidato.creado_en.desc()).limit(limite))]
    else:
        consulta = func.websearch_to_tsquery(text("'tf_es'::regconfig"), q)
        rank = func.max(func.ts_rank_cd(Documento.tsv, consulta)).label("rank")
        sub = (select(Documento.candidato_id, rank).where(Documento.tsv.op("@@")(consulta))
               .group_by(Documento.candidato_id).subquery())
        candidatos = db.execute(base.add_columns(sub.c.rank).join(sub, sub.c.candidato_id == Candidato.id)
                                .order_by(sub.c.rank.desc()).limit(limite)).all()
        filas = []
        for c, r in candidatos:
            fragmento = db.scalar(
                select(func.ts_headline(text("'tf_es'::regconfig"), Documento.texto_extraido, consulta,
                                        "StartSel=<mark>,StopSel=</mark>,MaxFragments=2,MaxWords=18,MinWords=6"))
                .where(Documento.candidato_id == c.id, Documento.tsv.op("@@")(consulta)).limit(1))
            filas.append((c, r, fragmento))
    return [{
        "id": c.id, "nombre": c.nombre, "email": c.email, "experiencia_anios": float(c.experiencia_anios),
        "habilidades": sorted(ch.habilidad.nombre for ch in c.habilidades),
        "postulaciones": len(c.postulaciones), "relevancia": round(float(r), 4) if r is not None else None,
        "fragmento": frag,
    } for c, r, frag in filas]


@router.get("/candidatos/{cid}")
def detalle(cid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    c = _candidato(db, cid, u)
    posts = [p for p in c.postulaciones if p.vacante.empresa_id == u.empresa_id]
    ids = [p.id for p in posts]
    entrevistas = db.scalars(select(Entrevista).where(Entrevista.postulacion_id.in_(ids))
                             .order_by(Entrevista.inicio.desc())).all() if ids else []
    pruebas = db.scalars(select(PruebaAsignacion).where(PruebaAsignacion.postulacion_id.in_(ids))).all() if ids else []
    correos = db.scalars(select(Correo).where(Correo.candidato_id == c.id).order_by(Correo.enviado_en.desc())).all()
    doc = c.documentos[0] if c.documentos else None
    return {
        "id": c.id, "nombre": c.nombre, "email": c.email, "telefono": c.telefono, "linkedin": c.linkedin,
        "ubicacion": c.ubicacion, "experiencia_anios": float(c.experiencia_anios),
        "anonimizado": c.anonimizado_en is not None,
        "privacidad": {"consentimiento_en": c.consentimiento_en.isoformat(), "version": c.consentimiento_version,
                       "retener_hasta": c.retener_hasta.isoformat()},
        "habilidades": sorted(({"id": ch.habilidad_id, "nombre": ch.habilidad.nombre, "origen": ch.origen}
                               for ch in c.habilidades), key=lambda h: h["nombre"]),
        "cv": {"id": doc.id, "nombre": doc.nombre_original, "mime": doc.mime, "datos": doc.datos_extraidos,
               "texto": doc.texto_extraido, "subido": doc.creado_en.isoformat(),
               "terminos": terminos_detectados(db, doc.texto_extraido or "")} if doc else None,
        "postulaciones": [serializers.postulacion(p) for p in sorted(posts, key=lambda p: p.creada_en, reverse=True)],
        "entrevistas": [serializers.entrevista(e) for e in entrevistas],
        "pruebas": [{"id": a.id, "postulacion_id": a.postulacion_id, "prueba": a.prueba.titulo,
                     "enviada_en": a.enviada_en.isoformat(), "expira_en": a.expira_en.isoformat(),
                     "completada_en": a.completada_en.isoformat() if a.completada_en else None,
                     "puntaje": float(a.puntaje) if a.puntaje is not None else None,
                     "puntaje_max": float(a.puntaje_max) if a.puntaje_max is not None else None,
                     "aprobada": (a.puntaje is not None and a.puntaje_max and
                                  float(a.puntaje) / float(a.puntaje_max) * 100 >= float(a.prueba.puntaje_aprobacion))}
                    for a in pruebas],
        "correos": [{"id": m.id, "asunto": m.asunto, "plantilla": m.plantilla, "estado": m.estado,
                     "cuerpo": m.cuerpo, "adjunto": m.adjunto, "enviado_en": m.enviado_en.isoformat()} for m in correos],
    }


@router.get("/documentos/{did}/descargar")
def descargar(did: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    d = obtener(db, Documento, did)
    _candidato(db, d.candidato_id, u)
    ruta = settings.upload_dir / d.ruta
    if not ruta.is_file():
        raise HTTPException(410, "El archivo ya no está disponible")
    return FileResponse(ruta, media_type=d.mime, filename=d.nombre_original)


@router.post("/candidatos/{cid}/habilidades", dependencies=[Depends(requiere(*GESTION))])
def agregar_habilidad(cid: int, datos: dict, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    c = _candidato(db, cid, u)
    h = resolver(db, str(datos.get("nombre", "")))
    if h is None:
        raise HTTPException(404, "Habilidad no registrada. Créala primero en el catálogo.")
    if h.id not in {ch.habilidad_id for ch in c.habilidades}:
        c.habilidades.append(CandidatoHabilidad(habilidad_id=h.id, origen="manual"))
        db.flush()
        db.refresh(c)
        for p in c.postulaciones:
            recalcular_match(p)
    db.commit()
    return {"ok": True}


@router.delete("/candidatos/{cid}/habilidades/{hid}", dependencies=[Depends(requiere(*GESTION))])
def quitar_habilidad(cid: int, hid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    c = _candidato(db, cid, u)
    c.habilidades = [ch for ch in c.habilidades if ch.habilidad_id != hid]
    db.flush()
    for p in c.postulaciones:
        recalcular_match(p)
    db.commit()
    return {"ok": True}


@router.delete("/candidatos/{cid}")
def borrar(cid: int, u: Usuario = Depends(requiere("admin")), db: Session = Depends(get_db)):
    """Borrado a solicitud del titular, ejecutado por un administrador."""
    c = _candidato(db, cid, u)
    privacidad.anonimizar(db, c, accion="anonimizacion", usuario_id=u.id, detalle={"origen": "admin"})
    db.commit()
    return {"ok": True}


@router.get("/postulaciones/{pid}")
def ver_postulacion(pid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return serializers.postulacion(postulacion_de(db, pid, u))


@router.patch("/postulaciones/{pid}/mover")
def mover(pid: int, datos: MoverIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    p = postulacion_de(db, pid, u)
    if p.candidato.anonimizado_en:
        raise HTTPException(409, "El candidato fue anonimizado")
    try:
        mover_etapa(db, p, datos.etapa, u.id, datos.comentario, datos.posicion, datos.notificar)
    except ErrorNegocio as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return serializers.tarjeta(p)
