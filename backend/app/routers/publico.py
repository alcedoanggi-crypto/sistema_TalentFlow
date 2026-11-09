"""Endpoints sin sesión: página de empleos, postulación, portal del candidato y pruebas.

El portal y las pruebas usan tokens opacos de 256 bits en la URL (sin contraseña).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import serializers
from app.config import settings
from app.database import get_db
from app.fuentes import FUENTES
from app.models import (
    Candidato, Empresa, Entrevista, Etapa, Postulacion, PruebaAsignacion, PruebaRespuesta, SolicitudPrivacidad, Vacante,
)
from app.schemas import RespuestasIn, SolicitudPrivacidadIn
from app.security import hash_email
from app.services import calificador, privacidad
from app.services.cv_parser import CVInvalido
from app.services.postulaciones import ErrorNegocio, crear_postulacion

router = APIRouter(prefix="/api/publico", tags=["público"])

AVISO_PRIVACIDAD = {
    "version": settings.version_consentimiento,
    "retencion_meses": settings.retencion_meses,
    "texto": [
        "Responsable: la empresa que publica la vacante, a través de la plataforma TalentFlow.",
        "Datos que tratamos: nombre, correo, teléfono, LinkedIn, el CV que subes y la información que extraemos "
        "automáticamente de él (experiencia, educación y habilidades).",
        "Finalidad: evaluar tu candidatura a esta y otras vacantes de la misma empresa y comunicarnos contigo sobre "
        "el proceso. No vendemos ni cedemos tus datos a terceros.",
        "Decisiones automatizadas: el puntaje de compatibilidad es una ayuda para el reclutador; ninguna candidatura "
        "se descarta automáticamente sin revisión humana.",
        f"Conservación: tus datos se guardan {settings.retencion_meses} meses desde tu última postulación y después se "
        "anonimizan automáticamente.",
        "Tus derechos: desde tu portal puedes descargar todos tus datos (acceso) o solicitar su eliminación (borrado) "
        "en cualquier momento.",
    ],
}


@router.get("/aviso-privacidad")
def aviso():
    return AVISO_PRIVACIDAD


@router.get("/empresas/{slug}")
def empleos(slug: str, db: Session = Depends(get_db)):
    empresa = db.scalar(select(Empresa).where(Empresa.slug == slug))
    if empresa is None:
        raise HTTPException(404, "Empresa no encontrada")
    vacantes = db.scalars(select(Vacante).where(Vacante.empresa_id == empresa.id, Vacante.estado == "publicada")
                          .order_by(Vacante.publicada_en.desc())).all()
    return {"empresa": {"nombre": empresa.nombre, "slug": empresa.slug, "descripcion": empresa.descripcion,
                        "sitio_web": empresa.sitio_web, "color": empresa.color_marca},
            "vacantes": [serializers.vacante(v, publico=True) for v in vacantes]}


def _vacante_publica(db: Session, slug: str, vslug: str) -> Vacante:
    v = db.scalar(select(Vacante).join(Empresa).where(Empresa.slug == slug, Vacante.slug == vslug,
                                                      Vacante.estado == "publicada"))
    if v is None:
        raise HTTPException(404, "La vacante no existe o ya cerró")
    return v


@router.get("/empresas/{slug}/vacantes/{vslug}")
def vacante(slug: str, vslug: str, db: Session = Depends(get_db)):
    return serializers.vacante(_vacante_publica(db, slug, vslug), publico=True)


@router.post("/empresas/{slug}/vacantes/{vslug}/postular", status_code=201)
async def postular(slug: str, vslug: str, request: Request, nombre: str = Form(..., min_length=3, max_length=150),
                   email: str = Form(..., max_length=160), telefono: str | None = Form(None),
                   linkedin: str | None = Form(None), fuente: str = Form("portal_empleo"),
                   carta: str | None = Form(None, max_length=4000), consentimiento: bool = Form(False),
                   cv: UploadFile = File(...), db: Session = Depends(get_db)):
    if "@" not in email:
        raise HTTPException(422, "Correo inválido")
    if fuente not in FUENTES:
        fuente = "otro"
    v = _vacante_publica(db, slug, vslug)
    contenido = await cv.read(settings.max_cv_mb * 1024 * 1024 + 1)
    try:
        p = crear_postulacion(db, vacante=v, nombre=nombre, email=email, telefono=telefono, linkedin=linkedin,
                              fuente=fuente, carta=carta, archivo_nombre=cv.filename or "cv.pdf", archivo=contenido,
                              consentimiento=consentimiento, ip=request.client.host if request.client else None)
    except (ErrorNegocio, CVInvalido) as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    db.commit()
    return {"mensaje": "¡Postulación recibida! Te enviamos un correo con el enlace a tu portal.",
            "portal": f"/portal/{p.candidato.token_portal}"}


# ------------------------------------------------------------ portal ---

def _por_token(db: Session, token: str) -> Candidato:
    c = db.scalar(select(Candidato).where(Candidato.token_portal == token, Candidato.anonimizado_en.is_(None)))
    if c is None:
        raise HTTPException(404, "Enlace inválido o datos eliminados")
    return c


@router.get("/portal/{token}")
def portal(token: str, db: Session = Depends(get_db)):
    c = _por_token(db, token)
    etapas = db.scalars(select(Etapa).where(Etapa.codigo != "descartado").order_by(Etapa.orden)).all()
    ahora = datetime.now(timezone.utc)
    salida = []
    for p in sorted(c.postulaciones, key=lambda p: p.creada_en, reverse=True):
        entrevistas = db.scalars(select(Entrevista).where(Entrevista.postulacion_id == p.id,
                                                          Entrevista.estado == "programada",
                                                          Entrevista.inicio >= ahora)).all()
        pruebas = db.scalars(select(PruebaAsignacion).where(PruebaAsignacion.postulacion_id == p.id)).all()
        salida.append({
            "id": p.id, "vacante": p.vacante.titulo, "empresa": p.vacante.empresa.nombre,
            "modalidad": p.vacante.modalidad, "fecha": p.creada_en.isoformat(),
            # Al candidato no se le muestra el puntaje interno ni el motivo de descarte.
            "etapa": {"codigo": p.etapa.codigo, "nombre": "Proceso finalizado" if p.etapa.codigo == "descartado"
                      else p.etapa.nombre, "orden": p.etapa.orden},
            "actualizada_en": p.actualizada_en.isoformat(),
            "entrevistas": [{"tipo": e.tipo, "inicio": e.inicio.isoformat(), "duracion_min": e.duracion_min,
                             "lugar": e.lugar} for e in entrevistas],
            "pruebas": [{"titulo": a.prueba.titulo, "enlace": f"/prueba/{a.token}",
                         "completada": a.completada_en is not None, "expira_en": a.expira_en.isoformat(),
                         "vencida": a.expira_en < ahora} for a in pruebas],
        })
    return {"nombre": c.nombre, "email": c.email, "retener_hasta": c.retener_hasta.isoformat(),
            "etapas": [{"codigo": e.codigo, "nombre": e.nombre, "orden": e.orden} for e in etapas],
            "postulaciones": salida}


@router.post("/portal/{token}/privacidad")
def solicitud_privacidad(token: str, datos: SolicitudPrivacidadIn, db: Session = Depends(get_db)):
    c = _por_token(db, token)
    if datos.tipo == "acceso":
        exportado = privacidad.exportar(db, c)
        db.add(SolicitudPrivacidad(candidato_id=c.id, email_hash=hash_email(c.email), tipo="acceso",
                                   estado="completada", resuelta_en=datetime.now(timezone.utc)))
        db.commit()
        return {"mensaje": "Estos son todos los datos que guardamos sobre ti.", "datos": exportado}
    if db.scalar(select(SolicitudPrivacidad.id).where(SolicitudPrivacidad.candidato_id == c.id,
                                                      SolicitudPrivacidad.tipo == "borrado",
                                                      SolicitudPrivacidad.estado == "pendiente")):
        return {"mensaje": "Ya tienes una solicitud de borrado en curso."}
    db.add(SolicitudPrivacidad(candidato_id=c.id, email_hash=hash_email(c.email), tipo="borrado", motivo=datos.motivo))
    db.commit()
    return {"mensaje": "Recibimos tu solicitud de borrado. Se atenderá en un máximo de 10 días hábiles."}


# ------------------------------------------------------------ pruebas ---

def _asignacion(db: Session, token: str) -> PruebaAsignacion:
    a = db.scalar(select(PruebaAsignacion).where(PruebaAsignacion.token == token))
    if a is None or a.postulacion.candidato.anonimizado_en:
        raise HTTPException(404, "Enlace de prueba inválido")
    return a


def _limite(a: PruebaAsignacion) -> datetime | None:
    if a.iniciada_en is None:
        return None
    return min(a.expira_en, a.iniciada_en + timedelta(minutes=a.prueba.tiempo_limite_min))


@router.get("/pruebas/{token}")
def ver_prueba(token: str, db: Session = Depends(get_db)):
    a = _asignacion(db, token)
    base = {"titulo": a.prueba.titulo, "descripcion": a.prueba.descripcion, "tiempo_limite_min": a.prueba.tiempo_limite_min,
            "vacante": a.postulacion.vacante.titulo, "empresa": a.postulacion.vacante.empresa.nombre,
            "candidato": a.postulacion.candidato.nombre, "expira_en": a.expira_en.isoformat(),
            "num_preguntas": len(a.prueba.preguntas)}
    if a.completada_en:
        return {**base, "estado": "completada", "puntaje": float(a.puntaje), "puntaje_max": float(a.puntaje_max)}
    if datetime.now(timezone.utc) > a.expira_en:
        return {**base, "estado": "vencida"}
    if a.iniciada_en is None:
        return {**base, "estado": "pendiente"}
    return {**base, "estado": "en_curso", "limite": _limite(a).isoformat(),
            "preguntas": serializers.prueba(a.prueba, con_respuestas=False)["preguntas"]}


@router.post("/pruebas/{token}/iniciar")
def iniciar(token: str, db: Session = Depends(get_db)):
    a = _asignacion(db, token)
    if a.completada_en or datetime.now(timezone.utc) > a.expira_en:
        raise HTTPException(409, "La prueba ya no está disponible")
    if a.iniciada_en is None:
        a.iniciada_en = datetime.now(timezone.utc)   # el cronómetro corre en el servidor
        db.commit()
    return ver_prueba(token, db)


@router.post("/pruebas/{token}/enviar")
def enviar(token: str, datos: RespuestasIn, db: Session = Depends(get_db)):
    a = _asignacion(db, token)
    if a.completada_en:
        raise HTTPException(409, "Ya enviaste esta prueba")
    if a.iniciada_en is None:
        raise HTTPException(409, "Primero inicia la prueba")
    # 2 minutos de gracia por latencia de red.
    tarde = datetime.now(timezone.utc) > _limite(a) + timedelta(minutes=2)
    total = Decimal(0)
    maximo = Decimal(0)
    a.respuestas = []
    for q in a.prueba.preguntas:
        maximo += Decimal(q.puntos)
        resp = datos.respuestas.get(q.id, {})
        if tarde:
            puntos, detalle = Decimal(0), {"error": "Enviada fuera de tiempo"}
        else:
            puntos, detalle = calificador.calificar_pregunta(q, resp)
        total += puntos
        a.respuestas.append(PruebaRespuesta(pregunta_id=q.id, respuesta=resp, puntos_obtenidos=puntos, detalle=detalle))
    a.puntaje, a.puntaje_max, a.completada_en = total, maximo, datetime.now(timezone.utc)
    db.commit()
    return {"estado": "completada", "puntaje": float(total), "puntaje_max": float(maximo), "fuera_de_tiempo": tarde}
