import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import serializers
from app.database import get_db
from app.deps import GESTION, requiere, usuario_actual
from app.models import (
    Competencia, Entrevista, Evaluacion, EvaluacionPuntaje, Postulacion, Usuario, Vacante,
)
from app.routers.candidatos import postulacion_de
from app.schemas import EntrevistaCambio, EntrevistaIn, EvaluacionIn
from app.services import correo
from app.services.ics import generar_ics

router = APIRouter(prefix="/api", tags=["entrevistas"])

TIPOS = {"tecnica": "Entrevista técnica", "rh": "Entrevista de RH", "cultural": "Entrevista cultural",
         "final": "Entrevista final"}


def _entrevista(db: Session, eid: int, u: Usuario) -> Entrevista:
    e = db.get(Entrevista, eid)
    if e is None or e.postulacion.vacante.empresa_id != u.empresa_id:
        raise HTTPException(404, "Entrevista no encontrada")
    return e


def _ics(e: Entrevista, cancelar: bool = False) -> str:
    p = e.postulacion
    titulo = f"{TIPOS[e.tipo]} · {p.vacante.titulo} · {p.vacante.empresa.nombre}"
    organizador = e.entrevistadores[0] if e.entrevistadores else None
    return generar_ics(
        uid=e.uid_ics, secuencia=e.secuencia_ics, inicio=e.inicio, duracion_min=e.duracion_min, titulo=titulo,
        descripcion=f"Candidato: {p.candidato.nombre}\nVacante: {p.vacante.titulo}\n{e.notas or ''}",
        lugar=e.lugar,
        organizador=(organizador.nombre, organizador.email) if organizador else ("TalentFlow", "no-responder@talentflow.local"),
        asistentes=[(p.candidato.nombre, p.candidato.email)] + [(x.nombre, x.email) for x in e.entrevistadores],
        cancelar=cancelar)


def _invitar(db: Session, e: Entrevista, motivo: str) -> None:
    """Envía la invitación (.ics adjunto) al candidato y a cada entrevistador."""
    cancelar = e.estado == "cancelada"
    adjunto = ("invitacion.ics", _ics(e, cancelar), "text/calendar; method=" + ("CANCEL" if cancelar else "REQUEST"))
    fecha = e.inicio.astimezone().strftime("%d/%m/%Y %H:%M")
    p = e.postulacion
    correo.enviar_plantilla(db, "entrevista", p, {
        "tipo_entrevista": TIPOS[e.tipo], "fecha": fecha, "duracion": e.duracion_min,
        "lugar": e.lugar or "Por confirmar", "motivo": motivo}, adjunto=adjunto)
    for x in e.entrevistadores:
        correo.enviar(db, para=x.email, asunto=f"[{motivo}] {TIPOS[e.tipo]} con {p.candidato.nombre} · {fecha}",
                      cuerpo=f"Hola {x.nombre.split()[0]},\n\n{TIPOS[e.tipo]} para {p.vacante.titulo}.\n"
                             f"Candidato: {p.candidato.nombre}\nFecha: {fecha} ({e.duracion_min} min)\n"
                             f"Lugar: {e.lugar or 'Por confirmar'}\n\nRecuerda registrar tu evaluación en TalentFlow.",
                      postulacion_id=p.id, adjunto=adjunto)


@router.get("/entrevistas")
def listar(desde: datetime | None = None, hasta: datetime | None = None, mias: bool = False,
           u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    q = (select(Entrevista).join(Postulacion).join(Vacante).where(Vacante.empresa_id == u.empresa_id)
         .order_by(Entrevista.inicio))
    if desde:
        q = q.where(Entrevista.inicio >= desde)
    if hasta:
        q = q.where(Entrevista.inicio < hasta)
    entrevistas = db.scalars(q).all()
    if mias or u.rol == "entrevistador":
        entrevistas = [e for e in entrevistas if u.id in {x.id for x in e.entrevistadores}]
    return [serializers.entrevista(e) for e in entrevistas]


@router.post("/entrevistas", status_code=201)
def programar(datos: EntrevistaIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    p = postulacion_de(db, datos.postulacion_id, u)
    entrevistadores = db.scalars(select(Usuario).where(Usuario.id.in_(datos.entrevistadores),
                                                       Usuario.empresa_id == u.empresa_id)).all()
    if len(entrevistadores) != len(set(datos.entrevistadores)):
        raise HTTPException(422, "Algún entrevistador no pertenece a la empresa")
    e = Entrevista(postulacion_id=p.id, tipo=datos.tipo, inicio=datos.inicio, duracion_min=datos.duracion_min,
                   lugar=datos.lugar, notas=datos.notas, creado_por=u.id,
                   uid_ics=f"{uuid.uuid4()}@talentflow", entrevistadores=list(entrevistadores))
    db.add(e)
    db.flush()
    db.refresh(e)
    _invitar(db, e, "Invitación")
    db.commit()
    return serializers.entrevista(e)


@router.patch("/entrevistas/{eid}")
def modificar(eid: int, datos: EntrevistaCambio, u: Usuario = Depends(requiere(*GESTION)),
              db: Session = Depends(get_db)):
    e = _entrevista(db, eid, u)
    reprogramada = any(v is not None and getattr(e, k) != v
                       for k, v in (("inicio", datos.inicio), ("duracion_min", datos.duracion_min), ("lugar", datos.lugar)))
    for campo in ("inicio", "duracion_min", "lugar", "estado"):
        if getattr(datos, campo) is not None:
            setattr(e, campo, getattr(datos, campo))
    if reprogramada or datos.estado == "cancelada":
        e.secuencia_ics += 1   # mismo UID + SEQUENCE mayor = el calendario actualiza el evento
        db.flush()
        _invitar(db, e, "Cancelada" if e.estado == "cancelada" else "Reprogramada")
    db.commit()
    return serializers.entrevista(e)


@router.get("/entrevistas/{eid}/ics")
def descargar_ics(eid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    e = _entrevista(db, eid, u)
    return Response(_ics(e, e.estado == "cancelada"), media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="entrevista-{e.id}.ics"'})


@router.post("/entrevistas/{eid}/evaluaciones", status_code=201)
def evaluar(eid: int, datos: EvaluacionIn, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    e = _entrevista(db, eid, u)
    if u.rol != "admin" and u.id not in {x.id for x in e.entrevistadores}:
        raise HTTPException(403, "Solo los entrevistadores asignados pueden evaluar")
    ev = db.scalar(select(Evaluacion).where(Evaluacion.entrevista_id == e.id, Evaluacion.evaluador_id == u.id))
    if ev is None:
        ev = Evaluacion(entrevista_id=e.id, evaluador_id=u.id)
        db.add(ev)
    ev.recomendacion, ev.fortalezas, ev.areas_mejora = datos.recomendacion, datos.fortalezas, datos.areas_mejora
    ev.puntajes = [EvaluacionPuntaje(competencia_id=p.competencia_id, puntaje=p.puntaje, comentario=p.comentario)
                   for p in {p.competencia_id: p for p in datos.puntajes}.values()]
    if e.estado == "programada":
        e.estado = "realizada"
    db.commit()
    db.refresh(e)
    return serializers.entrevista(e)


@router.get("/competencias", dependencies=[Depends(usuario_actual)])
def competencias(db: Session = Depends(get_db)):
    return [{"id": c.id, "nombre": c.nombre, "descripcion": c.descripcion}
            for c in db.scalars(select(Competencia).where(Competencia.activa).order_by(Competencia.id))]


@router.post("/competencias", status_code=201, dependencies=[Depends(requiere("admin"))])
def crear_competencia(datos: dict, db: Session = Depends(get_db)):
    nombre = str(datos.get("nombre", "")).strip()
    if not nombre:
        raise HTTPException(422, "Nombre requerido")
    c = Competencia(nombre=nombre, descripcion=datos.get("descripcion"))
    db.add(c)
    db.commit()
    return {"id": c.id, "nombre": c.nombre, "descripcion": c.descripcion}
