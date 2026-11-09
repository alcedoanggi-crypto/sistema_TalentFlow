from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Computed, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.habilidades import Habilidad
from app.models.organizacion import Empresa, Usuario


class Vacante(Base):
    __tablename__ = "vacantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    reclutador_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    titulo: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(170))
    departamento: Mapped[str | None] = mapped_column(String(80))
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    modalidad: Mapped[str] = mapped_column(String(12))
    tipo_contrato: Mapped[str] = mapped_column(String(30), default="tiempo_completo")
    descripcion: Mapped[str] = mapped_column(Text)
    requisitos: Mapped[str | None] = mapped_column(Text)
    experiencia_min_anios: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)
    salario_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salario_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="USD")
    mostrar_salario: Mapped[bool] = mapped_column(default=True)
    estado: Mapped[str] = mapped_column(String(12), default="borrador")
    publicada_en: Mapped[datetime | None]
    cerrada_en: Mapped[datetime | None]
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())

    empresa: Mapped[Empresa] = relationship()
    reclutador: Mapped[Usuario | None] = relationship()
    habilidades: Mapped[list["VacanteHabilidad"]] = relationship(
        back_populates="vacante", cascade="all, delete-orphan", lazy="selectin"
    )


class VacanteHabilidad(Base):
    __tablename__ = "vacante_habilidades"

    vacante_id: Mapped[int] = mapped_column(ForeignKey("vacantes.id", ondelete="CASCADE"), primary_key=True)
    habilidad_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id"), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12))

    vacante: Mapped[Vacante] = relationship(back_populates="habilidades")
    habilidad: Mapped[Habilidad] = relationship(lazy="joined")


class Candidato(Base):
    __tablename__ = "candidatos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(40))
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    experiencia_anios: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=0)
    token_portal: Mapped[str] = mapped_column(String(64), unique=True)
    consentimiento_en: Mapped[datetime]
    consentimiento_version: Mapped[str] = mapped_column(String(10))
    consentimiento_ip: Mapped[str | None] = mapped_column(String(45))
    retener_hasta: Mapped[date]
    anonimizado_en: Mapped[datetime | None]
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    habilidades: Mapped[list["CandidatoHabilidad"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    documentos: Mapped[list["Documento"]] = relationship(
        back_populates="candidato", cascade="all, delete-orphan", order_by="Documento.creado_en.desc()"
    )
    postulaciones: Mapped[list["Postulacion"]] = relationship(back_populates="candidato")


class CandidatoHabilidad(Base):
    __tablename__ = "candidato_habilidades"

    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id", ondelete="CASCADE"), primary_key=True)
    habilidad_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id"), primary_key=True)
    origen: Mapped[str] = mapped_column(String(10), default="cv")

    habilidad: Mapped[Habilidad] = relationship(lazy="joined")


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(12), default="cv")
    nombre_original: Mapped[str] = mapped_column(String(255))
    ruta: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(120))
    tamano_bytes: Mapped[int]
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    datos_extraidos: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Columna generada en PostgreSQL; se consulta con SQL, nunca se escribe desde Python.
    tsv = mapped_column(TSVECTOR, Computed("to_tsvector('tf_es'::regconfig, coalesce(texto_extraido, ''))"),
                        deferred=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    candidato: Mapped[Candidato] = relationship(back_populates="documentos")


class Etapa(Base):
    __tablename__ = "etapas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    orden: Mapped[int]
    es_final: Mapped[bool] = mapped_column(default=False)
    color: Mapped[str] = mapped_column(String(7))


class Postulacion(Base):
    __tablename__ = "postulaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacante_id: Mapped[int] = mapped_column(ForeignKey("vacantes.id", ondelete="CASCADE"))
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id", ondelete="CASCADE"))
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id", ondelete="SET NULL"))
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapas.id"))
    fuente: Mapped[str] = mapped_column(String(20), default="portal_empleo")
    carta: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    match_detalle: Mapped[dict] = mapped_column(JSONB, default=dict)
    posicion_kanban: Mapped[int] = mapped_column(default=0)
    motivo_descarte: Mapped[str | None] = mapped_column(String(255))
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    contratado_en: Mapped[datetime | None]

    vacante: Mapped[Vacante] = relationship()
    candidato: Mapped[Candidato] = relationship(back_populates="postulaciones")
    documento: Mapped[Documento | None] = relationship()
    etapa: Mapped[Etapa] = relationship(lazy="joined")
    historial: Mapped[list["HistorialEtapa"]] = relationship(
        cascade="all, delete-orphan", order_by="HistorialEtapa.creado_en"
    )


class HistorialEtapa(Base):
    __tablename__ = "historial_etapas"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id", ondelete="CASCADE"))
    etapa_desde_id: Mapped[int | None] = mapped_column(ForeignKey("etapas.id"))
    etapa_hasta_id: Mapped[int] = mapped_column(ForeignKey("etapas.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    comentario: Mapped[str | None] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    etapa_desde: Mapped[Etapa | None] = relationship(foreign_keys=[etapa_desde_id], lazy="joined")
    etapa_hasta: Mapped[Etapa] = relationship(foreign_keys=[etapa_hasta_id], lazy="joined")
    usuario: Mapped[Usuario | None] = relationship(lazy="joined")
