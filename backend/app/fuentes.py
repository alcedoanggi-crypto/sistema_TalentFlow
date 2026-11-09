"""Fuentes de reclutamiento (canales por los que llega un candidato).

Los portales externos (Computrabajo, Bumeran, OCC…) no ofrecen una API pública para leer
postulantes, así que TalentFlow los integra de dos formas legítimas:
  1. Enlace de postulación con `?fuente=<código>` para pegar en el aviso del portal.
  2. Importación masiva de los CV descargados desde el panel del portal.
Si agregas una fuente aquí, agrégala también en sql/03_fuentes.sql.
"""

FUENTES: dict[str, str] = {
    "portal_empleo": "Página de empleos",
    "computrabajo": "Computrabajo",
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "bumeran": "Bumeran",
    "occ": "OCC Mundial",
    "elempleo": "elempleo.com",
    "glassdoor": "Glassdoor",
    "referido": "Referido",
    "evento": "Evento / feria",
    "otro": "Otro",
}

# Portales externos: se muestran en el panel "Portales de empleo" de cada vacante.
PORTALES_EXTERNOS = ["computrabajo", "linkedin", "indeed", "bumeran", "occ", "elempleo", "glassdoor"]
