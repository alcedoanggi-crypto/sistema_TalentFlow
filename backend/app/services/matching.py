"""Puntuación de compatibilidad candidato-vacante.

score = Σ peso_i · cumplimiento_i, sobre los componentes que la vacante define:

  obligatorias   60 %   habilidades obligatorias presentes / total
  deseables      25 %   habilidades deseables presentes / total
  experiencia    15 %   min(1, años del candidato / años requeridos)

Si una vacante no define deseables (u obligatorias), su peso se reparte
proporcionalmente entre los demás componentes, así el score siempre va de 0 a 100.
El detalle devuelto es lo que la interfaz usa para resaltar qué cumple y qué falta.
"""
from dataclasses import dataclass

PESOS = {"obligatorias": 60.0, "deseables": 25.0, "experiencia": 15.0}


@dataclass
class Requisito:
    habilidad_id: int
    nombre: str
    tipo: str  # obligatoria | deseable


def calcular_match(habilidades_candidato: dict[int, str], experiencia_anios: float,
                   requisitos: list[Requisito], experiencia_min: float) -> dict:
    grupos = {"obligatorias": [r for r in requisitos if r.tipo == "obligatoria"],
              "deseables": [r for r in requisitos if r.tipo == "deseable"]}

    detalle: dict = {}
    componentes: dict[str, float] = {}
    for grupo, reqs in grupos.items():
        cumple = sorted(r.nombre for r in reqs if r.habilidad_id in habilidades_candidato)
        faltan = sorted(r.nombre for r in reqs if r.habilidad_id not in habilidades_candidato)
        detalle[grupo] = {"cumple": cumple, "faltan": faltan}
        if reqs:
            componentes[grupo] = len(cumple) / len(reqs)

    experiencia_min = float(experiencia_min or 0)
    experiencia_anios = float(experiencia_anios or 0)
    componentes["experiencia"] = 1.0 if experiencia_min <= 0 else min(1.0, experiencia_anios / experiencia_min)
    detalle["experiencia"] = {"requerida": experiencia_min, "candidato": experiencia_anios,
                              "cumple": experiencia_anios >= experiencia_min}

    peso_total = sum(PESOS[c] for c in componentes)
    score = sum(PESOS[c] * v for c, v in componentes.items()) / peso_total * 100

    ids_requeridos = {r.habilidad_id for r in requisitos}
    detalle["adicionales"] = sorted(n for hid, n in habilidades_candidato.items() if hid not in ids_requeridos)
    detalle["componentes"] = {c: round(v * 100, 1) for c, v in componentes.items()}
    detalle["pesos"] = {c: round(PESOS[c] / peso_total * 100, 1) for c in componentes}
    detalle["score"] = round(score, 1)
    return detalle
