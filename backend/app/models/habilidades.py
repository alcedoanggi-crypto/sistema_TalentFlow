from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Habilidad(Base):
    __tablename__ = "habilidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    categoria: Mapped[str] = mapped_column(String(40), default="tecnica")

    sinonimos: Mapped[list["HabilidadSinonimo"]] = relationship(
        back_populates="habilidad", cascade="all, delete-orphan", order_by="HabilidadSinonimo.sinonimo"
    )


class HabilidadSinonimo(Base):
    __tablename__ = "habilidad_sinonimos"

    id: Mapped[int] = mapped_column(primary_key=True)
    habilidad_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id", ondelete="CASCADE"))
    sinonimo: Mapped[str] = mapped_column(String(80), unique=True)

    habilidad: Mapped[Habilidad] = relationship(back_populates="sinonimos")
