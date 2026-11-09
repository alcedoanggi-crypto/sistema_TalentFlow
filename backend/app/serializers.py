"""Conversión de modelos ORM a JSON de respuesta."""
from app.models import Entrevista, Postulacion, Prueba, Vacante


def _f(v):
    return float(v) if v is not None else None


def vacante(v: Vacante, publico: bool = False) -> dict:
    d = {
        "id": v.id, "titulo": v.titulo, "slug": v.slug, "departamento": v.departamento,
        "ubicacion": v.ubicacion, "modalidad": v.modalidad, "tipo_contrato": v.tipo_contrato,
        "descripcion": v.descripcion, "requisitos": v.requisitos,
        "experiencia_min_anios": _f(v.experiencia_min_anios), "moneda": v.moneda,
        "salario_min": _f(v.salario_min) if (v.mostrar_salario or not publico) else None,
        "salario_max": _f(v.salario_max) if (v.mostrar_salario or not publico) else None,
        "mostrar_salario": v.mostrar_salario, "estado": v.estado,
        "publicada_en": v.publicada_en.isoformat() if v.publicada_en else None,
        "habilidades": sorted(({"id": vh.habilidad_id, "nombre": vh.habilidad.nombre, "tipo": vh.tipo}
                               for vh in v.habilidades), key=lambda h: (h["tipo"] != "obligatoria", h["nombre"])),
        "empresa": {"nombre": v.empresa.nombre, "slug": v.empresa.slug, "color": v.empresa.color_marca},
    }
    if not publico:
        d["reclutador"] = v.reclutador.nombre if v.reclutador else None
        d["creada_en"] = v.creada_en.isoformat()
    return d


def tarjeta(p: Postulacion) -> dict:
    """Tarjeta del Kanban."""
    det = p.match_detalle or {}
    return {
        "id": p.id, "candidato_id": p.candidato_id, "nombre": p.candidato.nombre,
        "etapa": p.etapa.codigo, "match_score": _f(p.match_score), "fuente": p.fuente,
        "posicion": p.posicion_kanban, "creada_en": p.creada_en.isoformat(),
        "faltan_obligatorias": len(det.get("obligatorias", {}).get("faltan", [])),
        "experiencia_anios": _f(p.candidato.experiencia_anios),
        "anonimizado": p.candidato.anonimizado_en is not None,
    }


def postulacion(p: Postulacion) -> dict:
    return {
        **tarjeta(p),
        "vacante": {"id": p.vacante.id, "titulo": p.vacante.titulo},
        "etapa_nombre": p.etapa.nombre, "carta": p.carta, "match_detalle": p.match_detalle,
        "motivo_descarte": p.motivo_descarte, "documento_id": p.documento_id,
        "contratado_en": p.contratado_en.isoformat() if p.contratado_en else None,
        "historial": [{"desde": h.etapa_desde.nombre if h.etapa_desde else None, "hasta": h.etapa_hasta.nombre,
                       "usuario": h.usuario.nombre if h.usuario else "Sistema", "comentario": h.comentario,
                       "fecha": h.creado_en.isoformat()} for h in p.historial],
    }


def entrevista(e: Entrevista) -> dict:
    return {
        "id": e.id, "postulacion_id": e.postulacion_id, "tipo": e.tipo, "inicio": e.inicio.isoformat(),
        "duracion_min": e.duracion_min, "lugar": e.lugar, "notas": e.notas, "estado": e.estado,
        "candidato": e.postulacion.candidato.nombre, "candidato_id": e.postulacion.candidato_id,
        "vacante": e.postulacion.vacante.titulo,
        "entrevistadores": [{"id": u.id, "nombre": u.nombre} for u in e.entrevistadores],
        "evaluaciones": [{
            "id": ev.id, "evaluador": ev.evaluador.nombre, "evaluador_id": ev.evaluador_id,
            "recomendacion": ev.recomendacion, "fortalezas": ev.fortalezas, "areas_mejora": ev.areas_mejora,
            "puntajes": [{"competencia": pt.competencia.nombre, "competencia_id": pt.competencia_id,
                          "puntaje": pt.puntaje, "comentario": pt.comentario} for pt in ev.puntajes],
            "promedio": round(sum(pt.puntaje for pt in ev.puntajes) / len(ev.puntajes), 2) if ev.puntajes else None,
        } for ev in e.evaluaciones],
    }


def prueba(pr: Prueba, con_respuestas: bool = True) -> dict:
    preguntas = []
    for q in pr.preguntas:
        d = {"id": q.id, "orden": q.orden, "tipo": q.tipo, "enunciado": q.enunciado, "opciones": q.opciones,
             "funcion": q.funcion, "plantilla_codigo": q.plantilla_codigo, "puntos": _f(q.puntos)}
        if con_respuestas:
            d["respuesta_correcta"] = q.respuesta_correcta
            d["casos_prueba"] = q.casos_prueba
        elif q.casos_prueba:
            # Al candidato solo se le muestra el primer caso como ejemplo.
            d["ejemplo"] = q.casos_prueba[0]
        preguntas.append(d)
    return {"id": pr.id, "titulo": pr.titulo, "descripcion": pr.descripcion,
            "tiempo_limite_min": pr.tiempo_limite_min, "puntaje_aprobacion": _f(pr.puntaje_aprobacion),
            "preguntas": preguntas, "puntaje_max": sum(_f(q.puntos) for q in pr.preguntas)}
