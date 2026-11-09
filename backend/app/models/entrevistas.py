from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.organizacion import Usuario
from app.models.reclutamiento import Postulacion


class Entrevista(Base):
    __tablename__ = "entrevistas"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(12))
    inicio: Mapped[datetime]
    duracion_min: Mapped[int] = mapped_column(default=60)
    lugar: Mapped[str | None] = mapped_column(String(255))
    notas: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="programada")
    uid_ics: Mapped[str] = mapped_column(String(80), unique=True)
    secuencia_ics: Mapped[int] = mapped_column(default=0)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    postulacion: Mapped[Postulacion] = relationship()
    entrevistadores: Mapped[list[Usuario]] = relationship(secondary="entrevista_entrevistadores", lazy="selectin")
    evaluaciones: Mapped[list["Evaluacion"]] = relationship(back_populates="entrevista", cascade="all, delete-orphan")


class EntrevistaEntrevistador(Base):
    __tablename__ = "entrevista_entrevistadores"

    entrevista_id: Mapped[int] = mapped_column(ForeignKey("entrevistas.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)


class Competencia(Base):
    __tablename__ = "competencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activa: Mapped[bool] = mapped_column(default=True)


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    entrevista_id: Mapped[int] = mapped_column(ForeignKey("entrevistas.id", ondelete="CASCADE"))
    evaluador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    recomendacion: Mapped[str] = mapped_column(String(12))
    fortalezas: Mapped[str | None] = mapped_column(Text)
    areas_mejora: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())

    entrevista: Mapped[Entrevista] = relationship(back_populates="evaluaciones")
    evaluador: Mapped[Usuario] = relationship(lazy="joined")
    puntajes: Mapped[list["EvaluacionPuntaje"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class EvaluacionPuntaje(Base):
    __tablename__ = "evaluacion_puntajes"

    evaluacion_id: Mapped[int] = mapped_column(ForeignKey("evaluaciones.id", ondelete="CASCADE"), primary_key=True)
    competencia_id: Mapped[int] = mapped_column(ForeignKey("competencias.id"), primary_key=True)
    puntaje: Mapped[int]
    comentario: Mapped[str | None] = mapped_column(String(500))

    competencia: Mapped[Competencia] = relationship(lazy="joined")
