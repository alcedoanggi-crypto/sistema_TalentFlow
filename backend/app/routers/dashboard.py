"""Métricas de reclutamiento. Todo se calcula en SQL sobre las vistas de sql/02_vistas.sql."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.fuentes import FUENTES
from app.deps import usuario_actual
from app.models import Usuario

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])



@router.get("")
def dashboard(vacante_id: int | None = None, dias: int = 180, u: Usuario = Depends(usuario_actual),
              db: Session = Depends(get_db)):
    params = {"emp": u.empresa_id, "vac": vacante_id, "dias": dias}
    filtro = """JOIN vacantes v ON v.id = p.vacante_id
                WHERE v.empresa_id = :emp AND (CAST(:vac AS INT) IS NULL OR v.id = :vac)
                  AND p.creada_en >= now() - make_interval(days => :dias)"""

    kpi = db.execute(text(f"""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE e.es_final = false) AS activas,
               count(*) FILTER (WHERE e.codigo = 'contratado') AS contratados,
               round(avg(p.match_score)::numeric, 1) AS match_promedio
        FROM postulaciones p JOIN etapas e ON e.id = p.etapa_id {filtro}"""), params).mappings().one()

    tiempo = db.execute(text(f"""
        SELECT round(avg(t.dias)::numeric, 1) AS promedio,
               round((percentile_cont(0.5) WITHIN GROUP (ORDER BY t.dias))::numeric, 1) AS mediana
        FROM v_tiempo_contratacion t JOIN postulaciones p ON p.id = t.postulacion_id {filtro}"""),
        params).mappings().one()

    por_etapa = db.execute(text(f"""
        SELECT e.codigo, e.nombre, e.color, count(p.id) AS total
        FROM etapas e LEFT JOIN (SELECT p.* FROM postulaciones p {filtro}) p ON p.etapa_id = e.id
        GROUP BY e.id ORDER BY e.orden"""), params).mappings().all()

    # Embudo: cuántas postulaciones ALCANZARON cada etapa (no solo cuántas están ahí ahora).
    embudo = db.execute(text(f"""
        SELECT e.codigo, e.nombre, e.color,
               count(a.postulacion_id) FILTER (WHERE a.orden_max >= e.orden) AS alcanzaron
        FROM etapas e CROSS JOIN (SELECT a.* FROM v_postulacion_alcance a
                                  JOIN postulaciones p ON p.id = a.postulacion_id {filtro}) a
        WHERE e.codigo <> 'descartado'
        GROUP BY e.id ORDER BY e.orden"""), params).mappings().all()
    embudo_out = []
    anterior = None
    for fila in embudo:
        d = dict(fila)
        d["conversion"] = round(d["alcanzaron"] / anterior * 100, 1) if anterior else None
        d["porcentaje"] = round(d["alcanzaron"] / embudo[0]["alcanzaron"] * 100, 1) if embudo[0]["alcanzaron"] else 0
        anterior = d["alcanzaron"] or None
        embudo_out.append(d)

    fuentes = db.execute(text(f"""
        SELECT p.fuente,
               count(*) AS postulaciones,
               count(*) FILTER (WHERE a.orden_max >= 3) AS entrevistados,
               count(*) FILTER (WHERE p.contratado_en IS NOT NULL) AS contratados,
               round(avg(p.match_score)::numeric, 1) AS match_promedio
        FROM postulaciones p JOIN v_postulacion_alcance a ON a.postulacion_id = p.id {filtro}
        GROUP BY p.fuente ORDER BY contratados DESC, entrevistados DESC"""), params).mappings().all()

    tendencia = db.execute(text(f"""
        SELECT to_char(date_trunc('week', p.creada_en), 'YYYY-MM-DD') AS semana,
               count(*) AS postulaciones,
               count(*) FILTER (WHERE p.contratado_en IS NOT NULL) AS contratados
        FROM postulaciones p {filtro}
        GROUP BY 1 ORDER BY 1"""), params).mappings().all()

    vacantes = db.execute(text("""
        SELECT v.id, v.titulo, v.estado, count(p.id) AS postulaciones,
               round(avg(p.match_score)::numeric, 1) AS match_promedio,
               round(avg(t.dias)::numeric, 1) AS dias_contratacion,
               EXTRACT(DAY FROM now() - v.publicada_en)::int AS dias_abierta
        FROM vacantes v LEFT JOIN postulaciones p ON p.vacante_id = v.id
        LEFT JOIN v_tiempo_contratacion t ON t.postulacion_id = p.id
        WHERE v.empresa_id = :emp AND v.estado <> 'borrador'
        GROUP BY v.id ORDER BY v.estado DESC, postulaciones DESC"""), params).mappings().all()

    def num(v):
        return float(v) if v is not None else None

    return {
        "kpis": {"total": kpi["total"], "activas": kpi["activas"], "contratados": kpi["contratados"],
                 "match_promedio": num(kpi["match_promedio"]),
                 "tiempo_contratacion": num(tiempo["promedio"]), "tiempo_mediana": num(tiempo["mediana"]),
                 "tasa_contratacion": round(kpi["contratados"] / kpi["total"] * 100, 1) if kpi["total"] else 0},
        "por_etapa": [dict(f) for f in por_etapa],
        "embudo": embudo_out,
        "fuentes": [{**dict(f), "nombre": FUENTES.get(f["fuente"], f["fuente"]),
                     "match_promedio": num(f["match_promedio"]),
                     "tasa_entrevista": round(f["entrevistados"] / f["postulaciones"] * 100, 1),
                     "tasa_contratacion": round(f["contratados"] / f["postulaciones"] * 100, 1)} for f in fuentes],
        "tendencia": [dict(f) for f in tendencia],
        "vacantes": [{**dict(f), "match_promedio": num(f["match_promedio"]),
                      "dias_contratacion": num(f["dias_contratacion"])} for f in vacantes],
    }
