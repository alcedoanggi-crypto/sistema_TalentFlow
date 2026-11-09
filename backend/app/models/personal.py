from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MiCV(Base):
    __tablename__ = "mi_cv"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    nombre_original: Mapped[str | None] = mapped_column(String(255))
    texto: Mapped[str] = mapped_column(Text)
    datos: Mapped[dict] = mapped_column(JSONB, default=dict)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class MiPostulacion(Base):
    __tablename__ = "mis_postulaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    empresa: Mapped[str] = mapped_column(String(150))
    puesto: Mapped[str] = mapped_column(String(150))
    url: Mapped[str | None] = mapped_column(String(500))
    descripcion: Mapped[str | None] = mapped_column(Text)
    modalidad: Mapped[str | None] = mapped_column(String(12))
    salario: Mapped[str | None] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(16), default="por_postular")
    fecha_postulacion: Mapped[date | None]
    proximo_seguimiento: Mapped[date | None]
    contacto: Mapped[str | None] = mapped_column(String(150))
    notas: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    match_detalle: Mapped[dict | None] = mapped_column(JSONB)
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    recordatorios: Mapped[list["MiRecordatorio"]] = relationship(
        cascade="all, delete-orphan", order_by="MiRecordatorio.fecha", lazy="selectin"
    )


class MiRecordatorio(Base):
    __tablename__ = "mis_recordatorios"

    id: Mapped[int] = mapped_column(primary_key=True)
    mi_postulacion_id: Mapped[int] = mapped_column(ForeignKey("mis_postulaciones.id", ondelete="CASCADE"))
    fecha: Mapped[date]
    texto: Mapped[str] = mapped_column(String(255))
    completado: Mapped[bool] = mapped_column(default=False)
