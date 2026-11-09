from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import serializers
from app.config import settings
from app.database import get_db
from app.deps import GESTION, obtener, requiere, usuario_actual
from app.models import Prueba, PruebaAsignacion, PruebaPregunta, Usuario
from app.routers.candidatos import postulacion_de
from app.schemas import AsignarPruebaIn, PruebaIn
from app.security import token_aleatorio
from app.services import calificador, correo

router = APIRouter(prefix="/api/pruebas", tags=["pruebas"])


@router.get("")
def listar(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    pruebas = db.scalars(select(Prueba).where(Prueba.empresa_id == u.empresa_id).order_by(Prueba.creada_en.desc()))
    salida = []
    for pr in pruebas:
        asig = db.scalars(select(PruebaAsignacion).where(PruebaAsignacion.prueba_id == pr.id)).all()
        hechas = [a for a in asig if a.completada_en]
        salida.append({**serializers.prueba(pr), "asignadas": len(asig), "completadas": len(hechas),
                       "promedio": round(sum(float(a.puntaje) / float(a.puntaje_max) * 100 for a in hechas) / len(hechas), 1)
                       if hechas else None})
    return salida


def _preguntas(datos: PruebaIn) -> list[PruebaPregunta]:
    return [PruebaPregunta(orden=i, **q.model_dump()) for i, q in enumerate(datos.preguntas, start=1)]


@router.post("", status_code=201)
def crear(datos: PruebaIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    pr = Prueba(empresa_id=u.empresa_id, **datos.model_dump(exclude={"preguntas"}), preguntas=_preguntas(datos))
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return serializers.prueba(pr)


@router.get("/{prid}")
def detalle(prid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    pr = obtener(db, Prueba, prid, u.empresa_id)
    asignaciones = db.scalars(select(PruebaAsignacion).where(PruebaAsignacion.prueba_id == pr.id)
                              .order_by(PruebaAsignacion.enviada_en.desc())).all()
    return {**serializers.prueba(pr), "asignaciones": [{
        "id": a.id, "postulacion_id": a.postulacion_id, "candidato": a.postulacion.candidato.nombre,
        "candidato_id": a.postulacion.candidato_id, "vacante": a.postulacion.vacante.titulo,
        "enviada_en": a.enviada_en.isoformat(), "completada_en": a.completada_en.isoformat() if a.completada_en else None,
        "puntaje": float(a.puntaje) if a.puntaje is not None else None,
        "puntaje_max": float(a.puntaje_max) if a.puntaje_max is not None else None,
        "respuestas": [{"pregunta_id": r.pregunta_id, "respuesta": r.respuesta, "puntos": float(r.puntos_obtenidos),
                        "detalle": r.detalle} for r in a.respuestas],
    } for a in asignaciones]}


@router.put("/{prid}")
def editar(prid: int, datos: PruebaIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    pr = obtener(db, Prueba, prid, u.empresa_id)
    if db.scalar(select(PruebaAsignacion.id).where(PruebaAsignacion.prueba_id == pr.id,
                                                   PruebaAsignacion.completada_en.is_not(None))):
        raise HTTPException(409, "Ya hay candidatos que la respondieron; duplícala para cambiar las preguntas")
    for k, v in datos.model_dump(exclude={"preguntas"}).items():
        setattr(pr, k, v)
    pr.preguntas = _preguntas(datos)
    db.commit()
    db.refresh(pr)
    return serializers.prueba(pr)


@router.post("/probar-codigo", dependencies=[Depends(requiere(*GESTION))])
def probar_codigo(datos: dict):
    """Permite al reclutador validar su solución de referencia contra los casos antes de publicar."""
    try:
        return calificador.ejecutar_codigo(datos.get("codigo", ""), datos.get("funcion", ""), datos.get("casos", []))
    except calificador.CodigoNoPermitido as exc:
        return {"error": str(exc)}


@router.post("/asignar", status_code=201)
def asignar(datos: AsignarPruebaIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    pr = obtener(db, Prueba, datos.prueba_id, u.empresa_id)
    p = postulacion_de(db, datos.postulacion_id, u)
    if db.scalar(select(PruebaAsignacion.id).where(PruebaAsignacion.prueba_id == pr.id,
                                                   PruebaAsignacion.postulacion_id == p.id)):
        raise HTTPException(409, "Esta prueba ya fue enviada a este candidato")
    a = PruebaAsignacion(prueba_id=pr.id, postulacion_id=p.id, token=token_aleatorio(),
                         expira_en=datetime.now(timezone.utc) + timedelta(days=datos.dias_vigencia))
    db.add(a)
    db.flush()
    correo.enviar_plantilla(db, "prueba_tecnica", p, {
        "prueba": pr.titulo, "enlace_prueba": f"{settings.frontend_url}/prueba/{a.token}",
        "tiempo_limite": pr.tiempo_limite_min, "fecha_limite": a.expira_en.astimezone().strftime("%d/%m/%Y %H:%M")})
    db.commit()
    return {"id": a.id, "token": a.token, "enlace": f"{settings.frontend_url}/prueba/{a.token}"}
