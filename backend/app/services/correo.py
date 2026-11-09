"""Envío de correos a candidatos a partir de plantillas con {{variables}}.

Sin SMTP configurado el correo no sale del sistema: se guarda en la tabla
`correos` con estado "simulado", visible en la bandeja de la interfaz. Así la
demo funciona sin credenciales y todo envío queda auditado.
"""
import logging
import re
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Correo, PlantillaCorreo, Postulacion

log = logging.getLogger(__name__)
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def renderizar(texto: str, variables: dict) -> str:
    """Sustituye {{variable}}; las desconocidas se dejan tal cual para detectarlas en la vista previa."""
    return _VAR.sub(lambda m: str(variables.get(m.group(1), m.group(0))), texto)


def variables_postulacion(p: Postulacion, extra: dict | None = None) -> dict:
    v = {
        "candidato": p.candidato.nombre.split()[0] if p.candidato.nombre else "",
        "candidato_completo": p.candidato.nombre,
        "vacante": p.vacante.titulo,
        "empresa": p.vacante.empresa.nombre,
        "etapa": p.etapa.nombre,
        "enlace_portal": f"{settings.frontend_url}/portal/{p.candidato.token_portal}",
    }
    v.update(extra or {})
    return v


def enviar(db: Session, *, para: str, asunto: str, cuerpo: str, candidato_id: int | None = None,
           postulacion_id: int | None = None, plantilla: str | None = None,
           adjunto: tuple[str, str, str] | None = None) -> Correo:
    """adjunto = (nombre_archivo, contenido_texto, mime). Registra siempre el correo."""
    estado, error = "simulado", None
    if settings.smtp_host:
        msg = EmailMessage()
        msg["From"] = settings.smtp_remitente
        msg["To"] = para
        msg["Subject"] = asunto
        msg.set_content(cuerpo)
        if adjunto:
            nombre, contenido, mime = adjunto
            principal, sub = mime.split("/", 1)
            msg.add_attachment(contenido.encode("utf-8"), maintype=principal, subtype=sub.split(";")[0],
                               filename=nombre)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                if settings.smtp_usuario:
                    smtp.login(settings.smtp_usuario, settings.smtp_password)
                smtp.send_message(msg)
            estado = "enviado"
        except Exception as exc:  # el fallo de correo no debe tumbar la operación de negocio
            log.error("Fallo SMTP hacia %s: %s", para, exc)
            estado, error = "error", str(exc)[:500]

    correo = Correo(candidato_id=candidato_id, postulacion_id=postulacion_id, plantilla=plantilla,
                    para=para, asunto=asunto, cuerpo=cuerpo, adjunto=adjunto[0] if adjunto else None,
                    estado=estado, error=error)
    db.add(correo)
    db.flush()
    return correo


def enviar_plantilla(db: Session, codigo: str, p: Postulacion, extra: dict | None = None,
                     adjunto: tuple[str, str, str] | None = None) -> Correo | None:
    plantilla = db.scalar(select(PlantillaCorreo).where(PlantillaCorreo.codigo == codigo))
    if plantilla is None or p.candidato.anonimizado_en:
        return None
    variables = variables_postulacion(p, extra)
    return enviar(db, para=p.candidato.email, asunto=renderizar(plantilla.asunto, variables),
                  cuerpo=renderizar(plantilla.cuerpo, variables), candidato_id=p.candidato_id,
                  postulacion_id=p.id, plantilla=codigo, adjunto=adjunto)
