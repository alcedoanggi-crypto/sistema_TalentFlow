"""Protección de datos personales del candidato.

Estrategia de borrado: **anonimización**, no DELETE en cascada. Se eliminan
los identificadores (nombre, correo, teléfono, LinkedIn), el CV y su texto,
las habilidades y los textos libres; se conservan solo los hechos estadísticos
(fuente, etapas y fechas) para que el dashboard no se descuadre. El correo se
guarda como hash SHA-256 en la bitácora para demostrar que la solicitud se
atendió sin conservar el dato.
"""
from datetime import date, datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    BitacoraPrivacidad, Candidato, CandidatoHabilidad, Correo, Documento, Entrevista, Evaluacion,
    Postulacion, PruebaAsignacion, PruebaRespuesta,
)
from app.security import hash_email, token_aleatorio


def anonimizar(db: Session, candidato: Candidato, *, accion: str, usuario_id: int | None = None,
               detalle: dict | None = None) -> None:
    if candidato.anonimizado_en:
        return
    huella = hash_email(candidato.email)

    for doc in db.scalars(select(Documento).where(Documento.candidato_id == candidato.id)):
        (settings.upload_dir / doc.ruta).unlink(missing_ok=True)
    db.execute(update(Postulacion).where(Postulacion.candidato_id == candidato.id)
               .values(documento_id=None, carta=None))
    db.execute(delete(Documento).where(Documento.candidato_id == candidato.id))
    db.execute(delete(CandidatoHabilidad).where(CandidatoHabilidad.candidato_id == candidato.id))
    db.execute(delete(Correo).where(Correo.candidato_id == candidato.id))

    ids_post = select(Postulacion.id).where(Postulacion.candidato_id == candidato.id)
    ids_ent = select(Entrevista.id).where(Entrevista.postulacion_id.in_(ids_post))
    db.execute(update(Entrevista).where(Entrevista.id.in_(ids_ent)).values(notas=None))
    db.execute(update(Evaluacion).where(Evaluacion.entrevista_id.in_(ids_ent))
               .values(fortalezas=None, areas_mejora=None))
    ids_asig = select(PruebaAsignacion.id).where(PruebaAsignacion.postulacion_id.in_(ids_post))
    db.execute(delete(PruebaRespuesta).where(PruebaRespuesta.asignacion_id.in_(ids_asig)))

    candidato.nombre = f"Candidato anonimizado #{candidato.id}"
    candidato.email = f"anonimizado-{candidato.id}@borrado.invalid"
    candidato.telefono = candidato.linkedin = candidato.ubicacion = candidato.consentimiento_ip = None
    candidato.token_portal = token_aleatorio()   # invalida el enlace del portal
    candidato.anonimizado_en = datetime.now(timezone.utc)
    db.add(BitacoraPrivacidad(accion=accion, email_hash=huella, usuario_id=usuario_id,
                              detalle={"candidato_id": candidato.id, **(detalle or {})}))
    db.flush()


def purgar_vencidos(db: Session, usuario_id: int | None = None, hoy: date | None = None) -> int:
    """Anonimiza a quienes superaron su plazo de retención. Pensado para un cron diario."""
    vencidos = db.scalars(select(Candidato).where(Candidato.retener_hasta < (hoy or date.today()),
                                                  Candidato.anonimizado_en.is_(None))).all()
    for c in vencidos:
        anonimizar(db, c, accion="purga_retencion", usuario_id=usuario_id,
                   detalle={"retener_hasta": c.retener_hasta.isoformat()})
    return len(vencidos)


def exportar(db: Session, candidato: Candidato) -> dict:
    """Derecho de acceso: todo lo que el sistema guarda sobre la persona."""
    db.add(BitacoraPrivacidad(accion="exportacion", email_hash=hash_email(candidato.email),
                              detalle={"candidato_id": candidato.id}))
    return {
        "datos_personales": {"nombre": candidato.nombre, "email": candidato.email, "telefono": candidato.telefono,
                             "linkedin": candidato.linkedin, "experiencia_anios": float(candidato.experiencia_anios)},
        "consentimiento": {"fecha": candidato.consentimiento_en.isoformat(),
                           "version": candidato.consentimiento_version,
                           "retener_hasta": candidato.retener_hasta.isoformat()},
        "habilidades": sorted(ch.habilidad.nombre for ch in candidato.habilidades),
        "documentos": [{"archivo": d.nombre_original, "subido": d.creado_en.isoformat(),
                        "datos_extraidos": d.datos_extraidos} for d in candidato.documentos],
        "postulaciones": [{"vacante": p.vacante.titulo, "etapa": p.etapa.nombre, "fecha": p.creada_en.isoformat(),
                           "fuente": p.fuente} for p in candidato.postulaciones],
    }
