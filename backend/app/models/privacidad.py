from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SolicitudPrivacidad(Base):
    __tablename__ = "solicitudes_privacidad"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidato_id: Mapped[int | None] = mapped_column(ForeignKey("candidatos.id", ondelete="SET NULL"))
    email_hash: Mapped[str] = mapped_column(String(64))
    tipo: Mapped[str] = mapped_column(String(12))
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    motivo: Mapped[str | None] = mapped_column(String(500))
    solicitada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    resuelta_en: Mapped[datetime | None]
    resuelta_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))


class BitacoraPrivacidad(Base):
    __tablename__ = "bitacora_privacidad"

    id: Mapped[int] = mapped_column(primary_key=True)
    accion: Mapped[str] = mapped_column(String(30))
    email_hash: Mapped[str | None] = mapped_column(String(64))
    detalle: Mapped[dict] = mapped_column(JSONB, default=dict)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
