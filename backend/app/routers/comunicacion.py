from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import GESTION, requiere, usuario_actual
from app.models import Correo, PlantillaCorreo, Postulacion, Usuario, Vacante
from app.routers.candidatos import postulacion_de
from app.schemas import CorreoManualIn, PlantillaIn
from app.services import correo

router = APIRouter(prefix="/api", tags=["comunicación"])

VARIABLES = ["candidato", "candidato_completo", "vacante", "empresa", "etapa", "enlace_portal",
             "tipo_entrevista", "fecha", "duracion", "lugar", "prueba", "enlace_prueba", "tiempo_limite", "fecha_limite"]


def _dict(p: PlantillaCorreo) -> dict:
    return {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "asunto": p.asunto, "cuerpo": p.cuerpo,
            "actualizada_en": p.actualizada_en.isoformat()}


@router.get("/plantillas", dependencies=[Depends(usuario_actual)])
def plantillas(db: Session = Depends(get_db)):
    return {"variables": VARIABLES,
            "plantillas": [_dict(p) for p in db.scalars(select(PlantillaCorreo).order_by(PlantillaCorreo.id))]}


@router.put("/plantillas/{codigo}", dependencies=[Depends(requiere(*GESTION))])
def editar(codigo: str, datos: PlantillaIn, db: Session = Depends(get_db)):
    p = db.scalar(select(PlantillaCorreo).where(PlantillaCorreo.codigo == codigo))
    if p is None:
        raise HTTPException(404, "Plantilla no encontrada")
    p.nombre, p.asunto, p.cuerpo = datos.nombre, datos.asunto, datos.cuerpo
    db.commit()
    db.refresh(p)
    return _dict(p)


@router.post("/plantillas/{codigo}/vista-previa")
def vista_previa(codigo: str, datos: dict, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    p = db.scalar(select(PlantillaCorreo).where(PlantillaCorreo.codigo == codigo))
    if p is None:
        raise HTTPException(404, "Plantilla no encontrada")
    asunto, cuerpo = datos.get("asunto", p.asunto), datos.get("cuerpo", p.cuerpo)
    if datos.get("postulacion_id"):
        variables = correo.variables_postulacion(postulacion_de(db, int(datos["postulacion_id"]), u))
    else:
        variables = {"candidato": "María", "candidato_completo": "María Pérez", "vacante": "Desarrolladora Backend",
                     "empresa": u.empresa.nombre, "etapa": "Entrevista técnica", "enlace_portal": "https://…/portal/xyz"}
    return {"asunto": correo.renderizar(asunto, variables), "cuerpo": correo.renderizar(cuerpo, variables)}


@router.post("/correos", status_code=201)
def enviar(datos: CorreoManualIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    p = postulacion_de(db, datos.postulacion_id, u)
    if p.candidato.anonimizado_en:
        raise HTTPException(409, "El candidato fue anonimizado")
    if datos.plantilla and not (datos.asunto and datos.cuerpo):
        m = correo.enviar_plantilla(db, datos.plantilla, p)
    else:
        if not (datos.asunto and datos.cuerpo):
            raise HTTPException(422, "Indica una plantilla o un asunto y cuerpo")
        v = correo.variables_postulacion(p)
        m = correo.enviar(db, para=p.candidato.email, asunto=correo.renderizar(datos.asunto, v),
                          cuerpo=correo.renderizar(datos.cuerpo, v), candidato_id=p.candidato_id,
                          postulacion_id=p.id, plantilla=datos.plantilla)
    db.commit()
    return {"id": m.id, "estado": m.estado}


@router.get("/correos")
def bandeja(limite: int = 100, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Bandeja de salida: todos los correos de la empresa (los "simulados" no salieron por falta de SMTP)."""
    q = (select(Correo).outerjoin(Postulacion, Postulacion.id == Correo.postulacion_id)
         .outerjoin(Vacante, Vacante.id == Postulacion.vacante_id)
         .where(Vacante.empresa_id == u.empresa_id).order_by(Correo.enviado_en.desc()).limit(min(limite, 500)))
    return [{"id": m.id, "para": m.para, "asunto": m.asunto, "cuerpo": m.cuerpo, "plantilla": m.plantilla,
             "estado": m.estado, "error": m.error, "adjunto": m.adjunto, "enviado_en": m.enviado_en.isoformat(),
             "candidato_id": m.candidato_id} for m in db.scalars(q)]
