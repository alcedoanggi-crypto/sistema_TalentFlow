import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import serializers
from app.config import settings
from app.database import get_db
from app.fuentes import FUENTES, PORTALES_EXTERNOS
from app.deps import GESTION, obtener, requiere, usuario_actual
from app.models import Etapa, Habilidad, HabilidadSinonimo, Postulacion, Usuario, Vacante, VacanteHabilidad
from app.schemas import VacanteIn
from app.services.habilidades import invalidar_indice, normalizar, resolver
from app.services.cv_parser import CVInvalido
from app.services.postulaciones import ErrorNegocio, crear_postulacion, procesar_cv, recalcular_match

router = APIRouter(prefix="/api/vacantes", tags=["vacantes"])


def slugify(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")[:160] or "vacante"


def _slug_unico(db: Session, empresa_id: int, base: str, excluir: int | None = None) -> str:
    slug, n = base, 2
    while db.scalar(select(Vacante.id).where(Vacante.empresa_id == empresa_id, Vacante.slug == slug,
                                             Vacante.id != (excluir or 0))):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _habilidad(db: Session, nombre: str) -> Habilidad:
    h = resolver(db, nombre)
    if h is None:   # habilidad nueva: se crea con su propio nombre como sinónimo
        h = Habilidad(nombre=nombre.strip())
        db.add(h)
        db.flush()
        db.add(HabilidadSinonimo(habilidad_id=h.id, sinonimo=normalizar(nombre)))
        db.flush()
        invalidar_indice()
    return h


def _aplicar(db: Session, v: Vacante, datos: VacanteIn) -> None:
    for campo in ("titulo", "departamento", "ubicacion", "modalidad", "tipo_contrato", "descripcion",
                  "requisitos", "experiencia_min_anios", "salario_min", "salario_max", "mostrar_salario"):
        setattr(v, campo, getattr(datos, campo))
    v.moneda = datos.moneda.upper()
    if datos.estado != v.estado:
        if datos.estado == "publicada" and not v.publicada_en:
            v.publicada_en = datetime.now(timezone.utc)
        v.cerrada_en = datetime.now(timezone.utc) if datos.estado == "cerrada" else None
        v.estado = datos.estado
    nuevas: dict[int, str] = {}
    for req in datos.habilidades:
        h = _habilidad(db, req.nombre)
        # Si se repite, obligatoria gana sobre deseable.
        if nuevas.get(h.id) != "obligatoria":
            nuevas[h.id] = req.tipo
    v.habilidades = [vh for vh in v.habilidades if vh.habilidad_id in nuevas]
    for vh in v.habilidades:
        vh.tipo = nuevas.pop(vh.habilidad_id)
    for hid, tipo in nuevas.items():
        v.habilidades.append(VacanteHabilidad(habilidad_id=hid, tipo=tipo))


def _recalcular_todas(db: Session, v: Vacante) -> None:
    db.flush()
    db.expire(v, ["habilidades"])
    for p in db.scalars(select(Postulacion).where(Postulacion.vacante_id == v.id)):
        if not p.candidato.anonimizado_en:
            recalcular_match(p)


@router.get("")
def listar(estado: str | None = None, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    q = select(Vacante).where(Vacante.empresa_id == u.empresa_id).order_by(Vacante.creada_en.desc())
    if estado:
        q = q.where(Vacante.estado == estado)
    vacantes = db.scalars(q).all()
    conteos = dict(db.execute(select(Postulacion.vacante_id, func.count()).group_by(Postulacion.vacante_id)).all())
    activas = dict(db.execute(
        select(Postulacion.vacante_id, func.count()).join(Etapa).where(Etapa.es_final.is_(False))
        .group_by(Postulacion.vacante_id)).all())
    return [{**serializers.vacante(v), "postulaciones": conteos.get(v.id, 0), "activas": activas.get(v.id, 0)}
            for v in vacantes]


@router.post("", status_code=201)
def crear(datos: VacanteIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    v = Vacante(empresa_id=u.empresa_id, reclutador_id=u.id, estado="borrador",
                slug=_slug_unico(db, u.empresa_id, slugify(datos.titulo)))
    db.add(v)
    _aplicar(db, v, datos)
    db.commit()
    db.refresh(v)
    return serializers.vacante(v)


@router.get("/{vid}")
def detalle(vid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return serializers.vacante(obtener(db, Vacante, vid, u.empresa_id))


@router.put("/{vid}")
def editar(vid: int, datos: VacanteIn, u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    v = obtener(db, Vacante, vid, u.empresa_id)
    if datos.titulo != v.titulo:
        v.slug = _slug_unico(db, u.empresa_id, slugify(datos.titulo), excluir=v.id)
    _aplicar(db, v, datos)
    _recalcular_todas(db, v)   # cambiaron los requisitos: el match de todos los candidatos se actualiza
    db.commit()
    db.refresh(v)
    return serializers.vacante(v)


@router.get("/{vid}/pipeline")
def pipeline(vid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    v = obtener(db, Vacante, vid, u.empresa_id)
    etapas = db.scalars(select(Etapa).order_by(Etapa.orden)).all()
    posts = db.scalars(select(Postulacion).where(Postulacion.vacante_id == v.id)
                       .order_by(Postulacion.posicion_kanban, Postulacion.match_score.desc())).all()
    columnas = {e.codigo: {"codigo": e.codigo, "nombre": e.nombre, "color": e.color, "es_final": e.es_final,
                           "tarjetas": []} for e in etapas}
    for p in posts:
        columnas[p.etapa.codigo]["tarjetas"].append(serializers.tarjeta(p))
    return {"vacante": serializers.vacante(v), "columnas": list(columnas.values())}


# ------------------------------------------------- portales externos ---

@router.get("/{vid}/portales")
def portales(vid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Enlaces de postulación por portal: se pegan en el aviso publicado en Computrabajo, LinkedIn, etc.
    Cada postulación queda registrada con su fuente y el dashboard mide qué portal funciona mejor."""
    v = obtener(db, Vacante, vid, u.empresa_id)
    base = f"{settings.frontend_url}/empleos/{v.empresa.slug}/{v.slug}"
    conteo = dict(db.execute(select(Postulacion.fuente, func.count()).where(Postulacion.vacante_id == v.id)
                             .group_by(Postulacion.fuente)).all())
    return {"publicada": v.estado == "publicada", "enlace_directo": base,
            "portales": [{"codigo": c, "nombre": FUENTES[c], "enlace": f"{base}?fuente={c}",
                          "postulaciones": conteo.get(c, 0)} for c in PORTALES_EXTERNOS]}


@router.post("/{vid}/importar")
async def importar(vid: int, fuente: str = Form(...), archivos: list[UploadFile] = File(...),
                   u: Usuario = Depends(requiere(*GESTION)), db: Session = Depends(get_db)):
    """Importa en lote los CV descargados desde el panel de un portal (p. ej. Computrabajo).

    Del CV se extraen nombre, correo y teléfono; sin correo no se puede crear al candidato
    (es su identificador y el canal para avisarle). Cada archivo se procesa en su propio
    SAVEPOINT: si uno falla, los demás se guardan igual.
    """
    if fuente not in FUENTES:
        raise HTTPException(422, "Fuente no válida")
    if len(archivos) > 50:
        raise HTTPException(422, "Máximo 50 CV por importación")
    v = obtener(db, Vacante, vid, u.empresa_id)
    resultados = []
    for a in archivos:
        nombre_archivo = a.filename or "cv.pdf"
        contenido = await a.read(settings.max_cv_mb * 1024 * 1024 + 1)
        sp = db.begin_nested()
        try:
            analisis = procesar_cv(db, nombre_archivo, contenido)
            datos = analisis[2]
            if not datos.get("email"):
                raise ErrorNegocio("No se encontró un correo en el CV")
            p = crear_postulacion(
                db, vacante=v, nombre=datos.get("nombre") or nombre_archivo.rsplit(".", 1)[0],
                email=datos["email"], telefono=datos.get("telefono"), linkedin=datos.get("linkedin"),
                fuente=fuente, carta=None, archivo_nombre=nombre_archivo, archivo=contenido,
                # El candidato aceptó los términos del portal al postularse ahí; el correo de
                # "recibido" le informa que ahora tratamos sus datos y le da su enlace para borrarlos.
                consentimiento=True, ip=None, analisis=analisis, version_consentimiento="ext")
            sp.commit()
            resultados.append({"archivo": nombre_archivo, "ok": True, "candidato_id": p.candidato_id,
                               "nombre": p.candidato.nombre, "match_score": float(p.match_score or 0)})
        except (ErrorNegocio, CVInvalido) as exc:
            sp.rollback()
            resultados.append({"archivo": nombre_archivo, "ok": False, "error": str(exc)})
    db.commit()
    return {"importados": sum(r["ok"] for r in resultados), "total": len(resultados), "resultados": resultados}
