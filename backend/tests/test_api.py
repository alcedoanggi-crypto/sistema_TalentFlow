"""Pruebas de integración contra la base real (requiere `python -m scripts.seed`).

Recorren el flujo completo: empleos públicos → postulación con CV → análisis →
match → pipeline → entrevista con .ics → evaluación → prueba técnica → portal
→ derecho de acceso y borrado.
"""
import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import a_pdf, texto_cv

cliente = TestClient(app)


@pytest.fixture(scope="module")
def admin():
    r = cliente.post("/api/auth/login", json={"email": "admin@talentflow.demo", "password": "Demo1234!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def entrevistador():
    r = cliente.post("/api/auth/login", json={"email": "carlos@talentflow.demo", "password": "Demo1234!"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_incorrecto():
    assert cliente.post("/api/auth/login", json={"email": "admin@talentflow.demo", "password": "x"}).status_code == 401


def test_endpoints_protegidos():
    assert cliente.get("/api/vacantes").status_code == 401


def test_rol_entrevistador_no_mueve_tarjetas(entrevistador):
    assert cliente.patch("/api/postulaciones/1/mover", json={"etapa": "revision"}, headers=entrevistador).status_code == 403


def test_sinonimos(admin):
    for termino, canonico in [("Postgres", "PostgreSQL"), ("JS", "JavaScript"), ("k8s", "Kubernetes"), ("nodejs", "Node.js")]:
        r = cliente.get("/api/habilidades/resolver", params={"q": termino}, headers=admin).json()
        assert r["habilidad"]["nombre"] == canonico


def test_busqueda_full_text(admin):
    r = cliente.get("/api/candidatos", params={"q": "experiencia python"}, headers=admin)
    assert r.status_code == 200
    filas = r.json()
    assert filas and filas[0]["relevancia"] > 0 and "<mark>" in filas[0]["fragmento"]
    # Filtro por habilidad usando un sinónimo
    con_postgres = cliente.get("/api/candidatos", params={"habilidad": "postgres"}, headers=admin).json()
    assert all("PostgreSQL" in c["habilidades"] for c in con_postgres)


def test_dashboard(admin):
    d = cliente.get("/api/dashboard", headers=admin).json()
    assert d["kpis"]["total"] > 0 and d["kpis"]["tiempo_contratacion"] > 0
    alcanzaron = [e["alcanzaron"] for e in d["embudo"]]
    assert alcanzaron == sorted(alcanzaron, reverse=True), "el embudo debe ser monótono decreciente"
    assert {f["fuente"] for f in d["fuentes"]}


def test_flujo_completo(admin, entrevistador):
    # 1. Página pública de empleos
    empleos = cliente.get("/api/publico/empresas/nebula-tech").json()
    vacante = next(v for v in empleos["vacantes"] if "Backend" in v["titulo"])
    assert all(v["estado"] == "publicada" for v in empleos["vacantes"])

    # 2. Postulación con CV PDF
    email = f"prueba.{uuid.uuid4().hex[:8]}@correo.example"
    pdf = a_pdf(texto_cv("Prueba Automatizada", email, "Backend Developer",
                         ["Python", "FastAPI", "Postgres", "Docker", "Git", "Redis"], 5))
    datos = {"nombre": "Prueba Automatizada", "email": email, "fuente": "linkedin", "consentimiento": "true"}
    url = f"/api/publico/empresas/nebula-tech/vacantes/{vacante['slug']}/postular"
    sin_consentimiento = cliente.post(url, data={**datos, "consentimiento": "false"},
                                      files={"cv": ("cv.pdf", io.BytesIO(pdf), "application/pdf")})
    assert sin_consentimiento.status_code == 400
    r = cliente.post(url, data=datos, files={"cv": ("cv.pdf", io.BytesIO(pdf), "application/pdf")})
    assert r.status_code == 201, r.text
    token = r.json()["portal"].rsplit("/", 1)[1]
    duplicada = cliente.post(url, data=datos, files={"cv": ("cv.pdf", io.BytesIO(pdf), "application/pdf")})
    assert duplicada.status_code == 400

    # 3. Análisis + match: "Postgres" del CV se normalizó a PostgreSQL
    busq = cliente.get("/api/candidatos", params={"q": "Prueba Automatizada"}, headers=admin).json()
    cand = next(c for c in busq if c["email"] == email)
    det = cliente.get(f"/api/candidatos/{cand['id']}", headers=admin).json()
    assert det["cv"]["datos"]["motor"] in ("spacy", "reglas")
    assert det["experiencia_anios"] == 5.0
    post = det["postulaciones"][0]
    assert "PostgreSQL" in post["match_detalle"]["obligatorias"]["cumple"]
    assert post["match_detalle"]["obligatorias"]["faltan"] == []
    assert post["match_score"] == 81.2   # 60 + 25·(1/4 deseables) + 15
    assert any(m["plantilla"] == "recibido" for m in det["correos"])

    # 4. Pipeline
    r = cliente.patch(f"/api/postulaciones/{post['id']}/mover", json={"etapa": "entrevista_tecnica"}, headers=admin)
    assert r.json()["etapa"] == "entrevista_tecnica"

    # 5. Entrevista con invitación .ics
    usuarios = cliente.get("/api/usuarios", headers=admin).json()
    carlos = next(u for u in usuarios if u["email"].startswith("carlos"))
    inicio = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0).isoformat()
    r = cliente.post("/api/entrevistas", json={"postulacion_id": post["id"], "tipo": "tecnica", "inicio": inicio,
                                               "lugar": "https://meet.example/x", "entrevistadores": [carlos["id"]]},
                     headers=admin)
    assert r.status_code == 201, r.text
    ent = r.json()
    ics = cliente.get(f"/api/entrevistas/{ent['id']}/ics", headers=admin)
    assert ics.headers["content-type"].startswith("text/calendar") and "BEGIN:VEVENT" in ics.text
    reprog = cliente.patch(f"/api/entrevistas/{ent['id']}", json={"duracion_min": 90}, headers=admin)
    assert reprog.status_code == 200
    assert "SEQUENCE:1" in cliente.get(f"/api/entrevistas/{ent['id']}/ics", headers=admin).text

    # 6. Evaluación por competencias (solo el entrevistador asignado)
    comps = cliente.get("/api/competencias", headers=admin).json()
    r = cliente.post(f"/api/entrevistas/{ent['id']}/evaluaciones", headers=entrevistador, json={
        "recomendacion": "si", "fortalezas": "Sólida", "puntajes": [{"competencia_id": c["id"], "puntaje": 4} for c in comps]})
    assert r.status_code == 201 and r.json()["evaluaciones"][0]["promedio"] == 4

    # 7. Prueba técnica: asignar, iniciar, responder, calificación automática
    prueba = cliente.get("/api/pruebas", headers=admin).json()[0]
    asig = cliente.post("/api/pruebas/asignar", json={"prueba_id": prueba["id"], "postulacion_id": post["id"]},
                        headers=admin).json()
    vista = cliente.post(f"/api/publico/pruebas/{asig['token']}/iniciar").json()
    assert vista["estado"] == "en_curso"
    assert all("respuesta_correcta" not in q for q in vista["preguntas"]), "no se filtran respuestas al candidato"
    respuestas = {}
    for q in vista["preguntas"]:
        if q["tipo"] == "opcion_multiple":
            respuestas[q["id"]] = {"opcion": 1}
        elif q["funcion"] == "es_palindromo":
            respuestas[q["id"]] = {"codigo": "def es_palindromo(t):\n    s=[c for c in t.lower() if c.isalnum()]\n"
                                             "    s=''.join(s).translate(str.maketrans('áéíóú','aeiou'))\n    return s==s[::-1]\n"}
    r = cliente.post(f"/api/publico/pruebas/{asig['token']}/enviar", json={"respuestas": respuestas}).json()
    assert r["estado"] == "completada" and 30 < r["puntaje"] < r["puntaje_max"]

    # 8. Portal del candidato
    portal = cliente.get(f"/api/publico/portal/{token}").json()
    assert portal["postulaciones"][0]["etapa"]["codigo"] == "entrevista_tecnica"
    assert "match_score" not in portal["postulaciones"][0]

    # 9. Privacidad: acceso y borrado
    acceso = cliente.post(f"/api/publico/portal/{token}/privacidad", json={"tipo": "acceso"}).json()
    assert acceso["datos"]["datos_personales"]["email"] == email
    cliente.post(f"/api/publico/portal/{token}/privacidad", json={"tipo": "borrado", "motivo": "test"})
    priv = cliente.get("/api/privacidad", headers=admin).json()
    sol = next(s for s in priv["solicitudes"] if s["candidato_id"] == cand["id"] and s["estado"] == "pendiente")
    assert cliente.post(f"/api/privacidad/solicitudes/{sol['id']}/resolver", json={"aprobar": True}, headers=admin).status_code == 200
    assert cliente.get(f"/api/publico/portal/{token}").status_code == 404
    anon = cliente.get(f"/api/candidatos/{cand['id']}", headers=admin).json()
    assert anon["anonimizado"] and anon["cv"] is None and "borrado.invalid" in anon["email"]


def test_modo_personal(admin):
    r = cliente.post("/api/personal/postulaciones", headers=admin, json={
        "empresa": "Test SA", "puesto": "QA", "estado": "postulada",
        "descripcion": "Requisitos: Selenium, Python y Kubernetes. 3 años.\nDeseable: JMeter"})
    assert r.status_code == 201
    mp = r.json()
    det = mp["match_detalle"]
    assert "Kubernetes" in det["obligatorias"]["faltan"] and "Selenium" in det["obligatorias"]["cumple"]
    assert det["deseables"]["faltan"] == ["JMeter"]
    assert mp["proximo_seguimiento"] and mp["recordatorios"]
    assert cliente.delete(f"/api/personal/postulaciones/{mp['id']}", headers=admin).status_code == 204


def test_importar_cv_de_portal(admin):
    """Importación masiva de CV descargados de Computrabajo: válido, duplicado y sin correo."""
    vacante = next(v for v in cliente.get("/api/vacantes?estado=publicada", headers=admin).json() if "Backend" in v["titulo"])
    email = f"ct.{uuid.uuid4().hex[:8]}@correo.example"
    bueno = a_pdf(texto_cv("Importada Computrabajo", email, "Backend", ["Python", "FastAPI", "Docker"], 3))
    sin_correo = a_pdf([("titulo", "Persona Sin Correo"), ("normal", "Experiencia en Python y Django")])
    archivos = [("archivos", ("bueno.pdf", bueno, "application/pdf")),
                ("archivos", ("repetido.pdf", bueno, "application/pdf")),
                ("archivos", ("sin_correo.pdf", sin_correo, "application/pdf"))]
    r = cliente.post(f"/api/vacantes/{vacante['id']}/importar", headers=admin, data={"fuente": "computrabajo"}, files=archivos)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["importados"] == 1 and res["total"] == 3
    ok, repetido, sin = res["resultados"]
    assert ok["ok"] and ok["match_score"] > 0
    assert not repetido["ok"] and "Ya te postulaste" in repetido["error"]
    assert not sin["ok"] and "correo" in sin["error"]

    det = cliente.get(f"/api/candidatos/{ok['candidato_id']}", headers=admin).json()
    assert det["postulaciones"][0]["fuente"] == "computrabajo"
    assert det["privacidad"]["version"] == "ext"
    assert any(c["plantilla"] == "recibido" for c in det["correos"])

    portales = cliente.get(f"/api/vacantes/{vacante['id']}/portales", headers=admin).json()
    ct = next(p for p in portales["portales"] if p["codigo"] == "computrabajo")
    assert ct["enlace"].endswith("?fuente=computrabajo") and ct["postulaciones"] >= 1
