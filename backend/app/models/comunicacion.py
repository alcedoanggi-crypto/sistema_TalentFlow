from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlantillaCorreo(Base):
    __tablename__ = "plantillas_correo"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    asunto: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text)
    actualizada_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Correo(Base):
    __tablename__ = "correos"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidato_id: Mapped[int | None] = mapped_column(ForeignKey("candidatos.id", ondelete="CASCADE"))
    postulacion_id: Mapped[int | None] = mapped_column(ForeignKey("postulaciones.id", ondelete="CASCADE"))
    plantilla: Mapped[str | None] = mapped_column(String(30))
    para: Mapped[str] = mapped_column(String(160))
    asunto: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text)
    adjunto: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[str] = mapped_column(String(10))
    error: Mapped[str | None] = mapped_column(String(500))
    enviado_en: Mapped[datetime] = mapped_column(server_default=func.now())
