from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.reclutamiento import Postulacion


class Prueba(Base):
    __tablename__ = "pruebas"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    titulo: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    tiempo_limite_min: Mapped[int] = mapped_column(default=45)
    puntaje_aprobacion: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=60)
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())

    preguntas: Mapped[list["PruebaPregunta"]] = relationship(
        back_populates="prueba", cascade="all, delete-orphan", order_by="PruebaPregunta.orden", lazy="selectin"
    )


class PruebaPregunta(Base):
    __tablename__ = "prueba_preguntas"

    id: Mapped[int] = mapped_column(primary_key=True)
    prueba_id: Mapped[int] = mapped_column(ForeignKey("pruebas.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(default=1)
    tipo: Mapped[str] = mapped_column(String(16))
    enunciado: Mapped[str] = mapped_column(Text)
    opciones: Mapped[list | None] = mapped_column(JSONB)
    respuesta_correcta: Mapped[int | None]
    funcion: Mapped[str | None] = mapped_column(String(60))
    plantilla_codigo: Mapped[str | None] = mapped_column(Text)
    casos_prueba: Mapped[list | None] = mapped_column(JSONB)
    puntos: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=10)

    prueba: Mapped[Prueba] = relationship(back_populates="preguntas")


class PruebaAsignacion(Base):
    __tablename__ = "prueba_asignaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    prueba_id: Mapped[int] = mapped_column(ForeignKey("pruebas.id", ondelete="CASCADE"))
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True)
    enviada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    expira_en: Mapped[datetime]
    iniciada_en: Mapped[datetime | None]
    completada_en: Mapped[datetime | None]
    puntaje: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    puntaje_max: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    prueba: Mapped[Prueba] = relationship(lazy="joined")
    postulacion: Mapped[Postulacion] = relationship()
    respuestas: Mapped[list["PruebaRespuesta"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class PruebaRespuesta(Base):
    __tablename__ = "prueba_respuestas"

    asignacion_id: Mapped[int] = mapped_column(
        ForeignKey("prueba_asignaciones.id", ondelete="CASCADE"), primary_key=True
    )
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("prueba_preguntas.id", ondelete="CASCADE"), primary_key=True)
    respuesta: Mapped[dict] = mapped_column(JSONB)
    puntos_obtenidos: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    detalle: Mapped[dict] = mapped_column(JSONB, default=dict)
