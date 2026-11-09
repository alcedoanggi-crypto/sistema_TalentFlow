"""Modelos ORM. Reflejan sql/01_schema.sql, que es la fuente de verdad del esquema."""
from app.models.organizacion import Empresa, Usuario
from app.models.habilidades import Habilidad, HabilidadSinonimo
from app.models.reclutamiento import (
    Candidato, CandidatoHabilidad, Documento, Etapa, HistorialEtapa,
    Postulacion, Vacante, VacanteHabilidad,
)
from app.models.entrevistas import (
    Competencia, Entrevista, EntrevistaEntrevistador, Evaluacion, EvaluacionPuntaje,
)
from app.models.pruebas import Prueba, PruebaAsignacion, PruebaPregunta, PruebaRespuesta
from app.models.comunicacion import Correo, PlantillaCorreo
from app.models.privacidad import BitacoraPrivacidad, SolicitudPrivacidad
from app.models.personal import MiCV, MiPostulacion, MiRecordatorio

__all__ = [
    "Empresa", "Usuario", "Habilidad", "HabilidadSinonimo", "Candidato", "CandidatoHabilidad",
    "Documento", "Etapa", "HistorialEtapa", "Postulacion", "Vacante", "VacanteHabilidad",
    "Competencia", "Entrevista", "EntrevistaEntrevistador", "Evaluacion", "EvaluacionPuntaje",
    "Prueba", "PruebaAsignacion", "PruebaPregunta", "PruebaRespuesta", "Correo", "PlantillaCorreo",
    "BitacoraPrivacidad", "SolicitudPrivacidad", "MiCV", "MiPostulacion", "MiRecordatorio",
]
