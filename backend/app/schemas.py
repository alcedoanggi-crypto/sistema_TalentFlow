"""Esquemas de entrada (validación). Las respuestas se arman en app/serializers.py."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

Modalidad = Literal["remoto", "hibrido", "presencial"]


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class HabilidadRequisito(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    tipo: Literal["obligatoria", "deseable"]


class VacanteIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    departamento: str | None = None
    ubicacion: str | None = None
    modalidad: Modalidad
    tipo_contrato: str = "tiempo_completo"
    descripcion: str = Field(min_length=10)
    requisitos: str | None = None
    experiencia_min_anios: Decimal = Field(default=Decimal(0), ge=0, le=40)
    salario_min: Decimal | None = Field(default=None, ge=0)
    salario_max: Decimal | None = Field(default=None, ge=0)
    moneda: str = Field(default="USD", min_length=3, max_length=3)
    mostrar_salario: bool = True
    estado: Literal["borrador", "publicada", "cerrada"] = "borrador"
    habilidades: list[HabilidadRequisito] = []

    @model_validator(mode="after")
    def _salario(self):
        if self.salario_min is not None and self.salario_max is not None and self.salario_min > self.salario_max:
            raise ValueError("El salario mínimo no puede superar al máximo")
        return self


class HabilidadIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    categoria: str = "tecnica"
    sinonimos: list[str] = []


class MoverIn(BaseModel):
    etapa: str
    posicion: int | None = None
    comentario: str | None = Field(default=None, max_length=500)
    notificar: bool = True


class EntrevistaIn(BaseModel):
    postulacion_id: int
    tipo: Literal["tecnica", "rh", "cultural", "final"]
    inicio: datetime
    duracion_min: int = Field(default=60, ge=15, le=480)
    lugar: str | None = None
    notas: str | None = None
    entrevistadores: list[int] = Field(min_length=1)

    @field_validator("inicio")
    @classmethod
    def _con_zona(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("La fecha debe incluir zona horaria (ISO 8601 con offset)")
        return v


class EntrevistaCambio(BaseModel):
    inicio: datetime | None = None
    duracion_min: int | None = Field(default=None, ge=15, le=480)
    lugar: str | None = None
    estado: Literal["programada", "realizada", "cancelada"] | None = None


class PuntajeIn(BaseModel):
    competencia_id: int
    puntaje: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=500)


class EvaluacionIn(BaseModel):
    recomendacion: Literal["fuerte_si", "si", "no", "fuerte_no"]
    fortalezas: str | None = None
    areas_mejora: str | None = None
    puntajes: list[PuntajeIn] = Field(min_length=1)


class PreguntaIn(BaseModel):
    tipo: Literal["opcion_multiple", "codigo"]
    enunciado: str
    opciones: list[str] | None = None
    respuesta_correcta: int | None = None
    funcion: str | None = Field(default=None, pattern=r"^[A-Za-z_]\w*$")
    plantilla_codigo: str | None = None
    casos_prueba: list[dict] | None = None
    puntos: Decimal = Field(default=Decimal(10), gt=0)

    @model_validator(mode="after")
    def _coherencia(self):
        if self.tipo == "opcion_multiple":
            if not self.opciones or len(self.opciones) < 2 or self.respuesta_correcta is None \
                    or not 0 <= self.respuesta_correcta < len(self.opciones):
                raise ValueError("Opción múltiple requiere ≥2 opciones y un índice correcto válido")
        elif not self.funcion or not self.casos_prueba:
            raise ValueError("Una pregunta de código requiere nombre de función y casos de prueba")
        return self


class PruebaIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    descripcion: str | None = None
    tiempo_limite_min: int = Field(default=45, ge=5, le=480)
    puntaje_aprobacion: Decimal = Field(default=Decimal(60), ge=0, le=100)
    preguntas: list[PreguntaIn] = Field(min_length=1)


class AsignarPruebaIn(BaseModel):
    prueba_id: int
    postulacion_id: int
    dias_vigencia: int = Field(default=5, ge=1, le=30)


class RespuestasIn(BaseModel):
    respuestas: dict[int, dict]   # pregunta_id -> {"opcion": 2} | {"codigo": "..."}


class PlantillaIn(BaseModel):
    nombre: str = Field(max_length=80)
    asunto: str = Field(max_length=200)
    cuerpo: str


class CorreoManualIn(BaseModel):
    postulacion_id: int
    plantilla: str | None = None
    asunto: str | None = None
    cuerpo: str | None = None


class SolicitudPrivacidadIn(BaseModel):
    tipo: Literal["borrado", "acceso"]
    motivo: str | None = Field(default=None, max_length=500)


class MiPostulacionIn(BaseModel):
    empresa: str = Field(min_length=1, max_length=150)
    puesto: str = Field(min_length=1, max_length=150)
    url: str | None = None
    descripcion: str | None = None
    modalidad: Modalidad | None = None
    salario: str | None = None
    estado: Literal["por_postular", "postulada", "en_proceso", "entrevista", "oferta", "aceptada",
                    "rechazada", "sin_respuesta"] = "por_postular"
    fecha_postulacion: date | None = None
    proximo_seguimiento: date | None = None
    contacto: str | None = None
    notas: str | None = None


class RecordatorioIn(BaseModel):
    fecha: date
    texto: str = Field(min_length=1, max_length=255)
    completado: bool = False
