"""Reglas de negocio de postulaciones: alta con análisis de CV, match y pipeline."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Candidato, CandidatoHabilidad, Documento, Etapa, HistorialEtapa, Postulacion, Vacante,
)
from app.security import token_aleatorio
from app.services import correo
from app.services.cv_parser import analizar, extraer_texto, validar_archivo
from app.services.habilidades import detectar_habilidades
from app.services.matching import Requisito, calcular_match


class ErrorNegocio(ValueError):
    pass


def _sumar_meses(d: date, meses: int) -> date:
    total = d.year * 12 + d.month - 1 + meses
    anio, mes = divmod(total, 12)
    return date(anio, mes + 1, min(d.day, 28))


def etapa_por_codigo(db: Session, codigo: str) -> Etapa:
    etapa = db.scalar(select(Etapa).where(Etapa.codigo == codigo))
    if etapa is None:
        raise ErrorNegocio(f"Etapa desconocida: {codigo}")
    return etapa


def requisitos_de(vacante: Vacante) -> list[Requisito]:
    return [Requisito(vh.habilidad_id, vh.habilidad.nombre, vh.tipo) for vh in vacante.habilidades]


def habilidades_de(candidato: Candidato) -> dict[int, str]:
    return {ch.habilidad_id: ch.habilidad.nombre for ch in candidato.habilidades}


def recalcular_match(p: Postulacion) -> None:
    detalle = calcular_match(habilidades_de(p.candidato), float(p.candidato.experiencia_anios),
                             requisitos_de(p.vacante), float(p.vacante.experiencia_min_anios))
    p.match_score = Decimal(str(detalle["score"]))
    p.match_detalle = detalle


def guardar_archivo(nombre: str, contenido: bytes) -> str:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    # Nombre aleatorio: nunca se usa el nombre que manda el cliente para escribir en disco.
    destino = f"{uuid.uuid4().hex}{'.pdf' if nombre.lower().endswith('.pdf') else '.docx'}"
    (settings.upload_dir / destino).write_bytes(contenido)
    return destino


def procesar_cv(db: Session, nombre: str, contenido: bytes) -> tuple[str, str, dict, dict[int, str]]:
    """Valida y analiza un CV. Devuelve (mime, texto, datos_extraidos, habilidades)."""
    mime = validar_archivo(nombre, contenido)
    texto = extraer_texto(nombre, contenido)
    datos = analizar(texto)
    habilidades = detectar_habilidades(db, texto)
    datos["habilidades"] = sorted(habilidades.values())
    return mime, texto, datos, habilidades


def crear_postulacion(db: Session, *, vacante: Vacante, nombre: str, email: str, telefono: str | None,
                      linkedin: str | None, fuente: str, carta: str | None, archivo_nombre: str,
                      archivo: bytes, consentimiento: bool, ip: str | None,
                      analisis: tuple | None = None, version_consentimiento: str | None = None) -> Postulacion:
    """`analisis` permite reutilizar un procesar_cv() ya hecho (importación masiva).
    `version_consentimiento` registra el origen del consentimiento si no es el aviso propio
    (p. ej. "ext" = el candidato aceptó los términos del portal externo donde se postuló)."""
    if not consentimiento:
        raise ErrorNegocio("Debes aceptar el aviso de privacidad para postularte.")
    if vacante.estado != "publicada":
        raise ErrorNegocio("Esta vacante ya no recibe postulaciones.")

    mime, texto, datos, habilidades = analisis or procesar_cv(db, archivo_nombre, archivo)
    version = version_consentimiento or settings.version_consentimiento
    email = email.strip().lower()
    ahora = datetime.now(timezone.utc)

    candidato = db.scalar(select(Candidato).where(Candidato.email == email))
    if candidato is None:
        candidato = Candidato(email=email, nombre=nombre.strip(), token_portal=token_aleatorio(),
                              consentimiento_en=ahora, consentimiento_version=version,
                              retener_hasta=_sumar_meses(ahora.date(), settings.retencion_meses))
        db.add(candidato)
    elif db.scalar(select(Postulacion.id).where(Postulacion.candidato_id == candidato.id,
                                                  Postulacion.vacante_id == vacante.id)):
        raise ErrorNegocio("Ya te postulaste a esta vacante. Revisa tu portal para ver el estado.")

    # Cada nueva postulación renueva el consentimiento y el plazo de retención.
    candidato.nombre = nombre.strip() or datos.get("nombre") or candidato.nombre
    candidato.telefono = telefono or datos.get("telefono") or candidato.telefono
    candidato.linkedin = linkedin or datos.get("linkedin") or candidato.linkedin
    candidato.experiencia_anios = Decimal(str(datos.get("experiencia_anios") or 0))
    candidato.consentimiento_en = ahora
    candidato.consentimiento_version = version
    candidato.consentimiento_ip = ip
    candidato.retener_hasta = _sumar_meses(ahora.date(), settings.retencion_meses)
    db.flush()

    existentes = {ch.habilidad_id for ch in candidato.habilidades}
    for hid in habilidades:
        if hid not in existentes:
            candidato.habilidades.append(CandidatoHabilidad(habilidad_id=hid, origen="cv"))

    doc = Documento(candidato_id=candidato.id, tipo="cv", nombre_original=archivo_nombre[:255],
                    ruta=guardar_archivo(archivo_nombre, archivo), mime=mime, tamano_bytes=len(archivo),
                    texto_extraido=texto, datos_extraidos=datos)
    db.add(doc)
    db.flush()

    etapa = etapa_por_codigo(db, "postulado")
    p = Postulacion(vacante=vacante, candidato=candidato, documento_id=doc.id, etapa=etapa,
                    fuente=fuente, carta=carta)
    db.add(p)
    db.flush()
    db.refresh(candidato)
    recalcular_match(p)
    p.historial.append(HistorialEtapa(etapa_hasta_id=etapa.id, comentario="Postulación recibida"))
    db.flush()
    correo.enviar_plantilla(db, "recibido", p)
    return p


# Correo automático al mover de etapa.
_PLANTILLA_POR_ETAPA = {"descartado": "rechazo", "oferta": "oferta"}


def mover_etapa(db: Session, p: Postulacion, codigo: str, usuario_id: int | None,
                comentario: str | None = None, posicion: int | None = None, notificar: bool = True) -> None:
    destino = etapa_por_codigo(db, codigo)
    if posicion is not None:
        p.posicion_kanban = posicion
    if destino.id == p.etapa_id:
        return
    origen_id = p.etapa_id
    p.etapa = destino
    p.etapa_id = destino.id
    p.contratado_en = datetime.now(timezone.utc) if codigo == "contratado" else None
    if codigo == "descartado":
        p.motivo_descarte = comentario
    p.historial.append(HistorialEtapa(etapa_desde_id=origen_id, etapa_hasta_id=destino.id,
                                      usuario_id=usuario_id, comentario=comentario))
    db.flush()
    if notificar and codigo != "postulado":
        correo.enviar_plantilla(db, _PLANTILLA_POR_ETAPA.get(codigo, "avance_etapa"), p)
