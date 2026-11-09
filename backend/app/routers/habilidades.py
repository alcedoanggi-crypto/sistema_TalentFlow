from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import GESTION, obtener, requiere, usuario_actual
from app.models import CandidatoHabilidad, Habilidad, HabilidadSinonimo, VacanteHabilidad
from app.schemas import HabilidadIn
from app.services.habilidades import invalidar_indice, normalizar, resolver

router = APIRouter(prefix="/api/habilidades", tags=["habilidades"])


def _dict(h: Habilidad, usos: int = 0) -> dict:
    return {"id": h.id, "nombre": h.nombre, "categoria": h.categoria, "usos": usos,
            "sinonimos": [{"id": s.id, "sinonimo": s.sinonimo} for s in h.sinonimos]}


@router.get("", dependencies=[Depends(usuario_actual)])
def listar(db: Session = Depends(get_db)):
    usos = dict(db.execute(select(CandidatoHabilidad.habilidad_id, func.count())
                           .group_by(CandidatoHabilidad.habilidad_id)).all())
    habs = db.scalars(select(Habilidad).options(selectinload(Habilidad.sinonimos)).order_by(Habilidad.nombre))
    return [_dict(h, usos.get(h.id, 0)) for h in habs]


@router.get("/resolver", dependencies=[Depends(usuario_actual)])
def resolver_termino(q: str, db: Session = Depends(get_db)):
    h = resolver(db, q)
    return {"termino": q, "habilidad": {"id": h.id, "nombre": h.nombre} if h else None}


def _validar_sinonimo(db: Session, s: str) -> str:
    s = normalizar(s)
    if not s:
        raise HTTPException(422, "Sinónimo vacío")
    otro = db.scalar(select(HabilidadSinonimo).where(HabilidadSinonimo.sinonimo == s))
    if otro:
        raise HTTPException(409, f"'{s}' ya es sinónimo de {otro.habilidad.nombre}")
    return s


@router.post("", status_code=201, dependencies=[Depends(requiere(*GESTION))])
def crear(datos: HabilidadIn, db: Session = Depends(get_db)):
    if resolver(db, datos.nombre):
        raise HTTPException(409, f"'{datos.nombre}' ya existe o es sinónimo de otra habilidad")
    h = Habilidad(nombre=datos.nombre.strip(), categoria=datos.categoria)
    db.add(h)
    db.flush()
    for s in {normalizar(datos.nombre), *datos.sinonimos}:
        db.add(HabilidadSinonimo(habilidad_id=h.id, sinonimo=_validar_sinonimo(db, s)))
        db.flush()
    db.commit()
    invalidar_indice()
    db.refresh(h)
    return _dict(h)


@router.post("/{hid}/sinonimos", status_code=201, dependencies=[Depends(requiere(*GESTION))])
def agregar_sinonimo(hid: int, datos: dict, db: Session = Depends(get_db)):
    h = obtener(db, Habilidad, hid)
    db.add(HabilidadSinonimo(habilidad_id=h.id, sinonimo=_validar_sinonimo(db, str(datos.get("sinonimo", "")))))
    db.commit()
    invalidar_indice()
    db.refresh(h)
    return _dict(h)


@router.delete("/sinonimos/{sid}", status_code=204, dependencies=[Depends(requiere(*GESTION))])
def borrar_sinonimo(sid: int, db: Session = Depends(get_db)):
    s = db.get(HabilidadSinonimo, sid)
    if s:
        db.delete(s)
        db.commit()
        invalidar_indice()


@router.delete("/{hid}", status_code=204, dependencies=[Depends(requiere("admin"))])
def borrar(hid: int, db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(VacanteHabilidad).where(VacanteHabilidad.habilidad_id == hid)):
        raise HTTPException(409, "La habilidad está en uso por alguna vacante")
    h = db.get(Habilidad, hid)
    if h:
        db.query(CandidatoHabilidad).filter_by(habilidad_id=hid).delete()
        db.delete(h)
        db.commit()
        invalidar_indice()
