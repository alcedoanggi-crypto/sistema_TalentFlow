import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    auth, candidatos, comunicacion, dashboard, entrevistas, habilidades, personal, privacidad, pruebas, publico,
    vacantes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="TalentFlow ATS", version="1.0.0",
              description="Sistema de seguimiento de candidatos con análisis de CV y match de habilidades.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_lista, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, publico, vacantes, habilidades, candidatos, entrevistas, pruebas, comunicacion, dashboard,
          privacidad, personal):
    app.include_router(r.router)


@app.get("/api/salud", tags=["sistema"])
def salud():
    from app.services.cv_parser import _nlp
    return {"ok": True, "motor_cv": "spacy" if _nlp() is not None else "reglas"}
