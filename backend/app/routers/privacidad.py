from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import requiere
from app.models import BitacoraPrivacidad, Candidato, SolicitudPrivacidad, Usuario
from app.services import privacidad

router = APIRouter(prefix="/api/privacidad", tags=["privacidad"])


@router.get("")
def resumen(u: Usuario = Depends(requiere("admin")), db: Session = Depends(get_db)):
    hoy = date.today()
    solicitudes = db.scalars(select(SolicitudPrivacidad).order_by(SolicitudPrivacidad.solicitada_en.desc()).limit(100))
    bitacora = db.scalars(select(BitacoraPrivacidad).order_by(BitacoraPrivacidad.creado_en.desc()).limit(100))
    por_vencer = db.scalars(select(Candidato).where(Candidato.anonimizado_en.is_(None),
                                                    Candidato.retener_hasta < hoy + timedelta(days=30))
                            .order_by(Candidato.retener_hasta)).all()
    return {
        "metricas": {
            "candidatos_activos": db.scalar(select(func.count()).where(Candidato.anonimizado_en.is_(None))),
            "anonimizados": db.scalar(select(func.count()).where(Candidato.anonimizado_en.is_not(None))),
            "vencidos": sum(1 for c in por_vencer if c.retener_hasta < hoy),
            "por_vencer_30d": sum(1 for c in por_vencer if c.retener_hasta >= hoy),
            "pendientes": db.scalar(select(func.count()).select_from(SolicitudPrivacidad)
                                    .where(SolicitudPrivacidad.estado == "pendiente")),
        },
        "solicitudes": [{"id": s.id, "candidato_id": s.candidato_id, "tipo": s.tipo, "estado": s.estado,
                         "motivo": s.motivo, "solicitada_en": s.solicitada_en.isoformat(),
                         "resuelta_en": s.resuelta_en.isoformat() if s.resuelta_en else None,
                         "candidato": db.get(Candidato, s.candidato_id).nombre if s.candidato_id else None,
                         "email_hash": s.email_hash[:12] + "…"} for s in solicitudes],
        "por_vencer": [{"id": c.id, "nombre": c.nombre, "retener_hasta": c.retener_hasta.isoformat(),
                        "vencido": c.retener_hasta < hoy} for c in por_vencer],
        "bitacora": [{"id": b.id, "accion": b.accion, "email_hash": (b.email_hash or "")[:12] + "…",
                      "detalle": b.detalle, "creado_en": b.creado_en.isoformat()} for b in bitacora],
    }


@router.post("/solicitudes/{sid}/resolver")
def resolver(sid: int, datos: dict, u: Usuario = Depends(requiere("admin")), db: Session = Depends(get_db)):
    s = db.get(SolicitudPrivacidad, sid)
    if s is None or s.estado != "pendiente":
        raise HTTPException(404, "Solicitud no encontrada o ya resuelta")
    if datos.get("aprobar", True):
        c = db.get(Candidato, s.candidato_id) if s.candidato_id else None
        if c:
            privacidad.anonimizar(db, c, accion="anonimizacion", usuario_id=u.id,
                                  detalle={"origen": "solicitud_titular", "solicitud_id": s.id})
        s.estado = "completada"
    else:
        s.estado = "rechazada"   # p. ej. obligación legal de conservar (proceso judicial en curso)
        s.motivo = (s.motivo or "") + f" | Rechazo: {datos.get('motivo', 'sin motivo')}"
    s.resuelta_en, s.resuelta_por = datetime.now(timezone.utc), u.id
    db.commit()
    return {"ok": True, "estado": s.estado}


@router.post("/purgar")
def purgar(u: Usuario = Depends(requiere("admin")), db: Session = Depends(get_db)):
    n = privacidad.purgar_vencidos(db, usuario_id=u.id)
    db.commit()
    return {"anonimizados": n}
