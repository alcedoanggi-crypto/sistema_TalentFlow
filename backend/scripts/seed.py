"""Datos de demostración. BORRA el contenido actual de la base (excepto etapas).

Uso:  python -m scripts.seed

Los CV se generan como PDF (reportlab) y Word (python-docx) reales y pasan por
el mismo flujo que una postulación pública: validación, extracción de texto,
análisis con spaCy, detección de habilidades y match. Luego se "envejecen" las
fechas para que el dashboard tenga historia.
"""
import io
import random
from datetime import date, datetime, timedelta, timezone

from docx import Document as DocxDocument
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy import select, text

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Competencia, Empresa, Entrevista, Evaluacion, EvaluacionPuntaje, Habilidad, HabilidadSinonimo, MiCV,
    MiPostulacion, MiRecordatorio, PlantillaCorreo, Prueba, PruebaAsignacion, PruebaPregunta, PruebaRespuesta,
    SolicitudPrivacidad, Usuario, Vacante, VacanteHabilidad,
)
from app.security import hash_email, hash_password, token_aleatorio
from app.services import calificador
from app.services.habilidades import invalidar_indice, normalizar
from app.services.postulaciones import crear_postulacion, mover_etapa, procesar_cv

random.seed(42)
AHORA = datetime.now(timezone.utc)

# ------------------------------------------------------------------ catálogo
HABILIDADES = {
    "tecnica": {
        "Python": ["py", "python3"], "JavaScript": ["js", "ecmascript", "es6"], "TypeScript": ["ts"],
        "Java": [], "C#": ["csharp", "c sharp"], "Go": ["golang"], "PHP": [], "SQL": [],
        "PostgreSQL": ["postgres", "psql", "postgre"], "MySQL": [], "MongoDB": ["mongo"], "Redis": [],
        "React": ["react.js", "reactjs"], "Vue.js": ["vue", "vuejs"], "Angular": [], "Node.js": ["node", "nodejs"],
        "Django": [], "FastAPI": [], "Flask": [], "Spring Boot": ["spring"], ".NET": ["dotnet", "asp.net"],
        "HTML": ["html5"], "CSS": ["css3"], "TailwindCSS": ["tailwind"], "REST APIs": ["rest", "api rest", "restful"],
        "GraphQL": [], "Docker": ["contenedores"], "Kubernetes": ["k8s"], "AWS": ["amazon web services"],
        "Azure": [], "GCP": ["google cloud"], "Git": ["github", "gitlab"], "CI/CD": ["integracion continua", "github actions"],
        "Linux": [], "Pandas": [], "NumPy": [], "Power BI": ["powerbi"], "Tableau": [], "Excel": ["excel avanzado"],
        "Machine Learning": ["ml", "aprendizaje automatico"], "Selenium": [], "Cypress": [], "Pytest": [],
        "Postman": [], "JMeter": [], "Testing automatizado": ["automatizacion de pruebas", "test automation"],
        "Figma": [], "Adobe XD": ["xd"], "UX Research": ["investigacion de usuarios", "user research"],
        "Prototipado": ["wireframes", "prototipos"], "WordPress": ["wp"], "Jira": [], "Scrum": ["metodologias agiles", "agile"],
    },
    "blanda": {
        "Comunicación efectiva": ["comunicacion"], "Trabajo en equipo": ["colaboracion"], "Liderazgo": [],
        "Inglés": ["ingles avanzado", "english", "ingles b2", "ingles c1"],
    },
}

PLANTILLAS = {
    "recibido": ("Postulación recibida", "Recibimos tu postulación a {{vacante}}",
                 "Hola {{candidato}},\n\nGracias por tu interés en {{vacante}} en {{empresa}}. Recibimos tu CV y "
                 "nuestro equipo lo revisará en los próximos días.\n\nPuedes consultar el estado de tu proceso en "
                 "cualquier momento aquí:\n{{enlace_portal}}\n\nSaludos,\nEquipo de Talento · {{empresa}}"),
    "avance_etapa": ("Avance de etapa", "Tu proceso para {{vacante}} avanzó",
                     "Hola {{candidato}},\n\n¡Buenas noticias! Tu candidatura para {{vacante}} pasó a la etapa "
                     "«{{etapa}}». Pronto te contactaremos con los siguientes pasos.\n\nSigue tu proceso: "
                     "{{enlace_portal}}\n\nSaludos,\nEquipo de Talento · {{empresa}}"),
    "rechazo": ("Rechazo amable", "Actualización sobre tu postulación a {{vacante}}",
                "Hola {{candidato}},\n\nQueremos agradecerte sinceramente el tiempo que dedicaste al proceso para "
                "{{vacante}}. Tras una revisión cuidadosa, decidimos continuar con perfiles que se ajustan más a las "
                "necesidades actuales del puesto.\n\nEsta decisión no refleja tu valor profesional. Guardaremos tu CV "
                "(con tu consentimiento) para futuras oportunidades y te animamos a postularte de nuevo.\n\n"
                "Te deseamos mucho éxito,\nEquipo de Talento · {{empresa}}"),
    "oferta": ("Oferta", "¡Tenemos una propuesta para ti! · {{vacante}}",
               "Hola {{candidato}},\n\nNos alegra mucho comunicarte que queremos que te unas a {{empresa}} como "
               "{{vacante}}. En breve te enviaremos la carta oferta con el detalle de la compensación y fecha de "
               "inicio.\n\n¡Felicidades!\nEquipo de Talento · {{empresa}}"),
    "entrevista": ("Invitación a entrevista", "{{motivo}}: {{tipo_entrevista}} · {{vacante}}",
                   "Hola {{candidato}},\n\nTe invitamos a una {{tipo_entrevista}} para {{vacante}}.\n\n"
                   "Fecha: {{fecha}}\nDuración: {{duracion}} minutos\nLugar: {{lugar}}\n\nAdjuntamos el archivo .ics "
                   "para que lo agregues a tu calendario.\n\nSaludos,\nEquipo de Talento · {{empresa}}"),
    "prueba_tecnica": ("Prueba técnica", "Prueba técnica para {{vacante}}",
                       "Hola {{candidato}},\n\nComo siguiente paso te compartimos la prueba «{{prueba}}». Tienes "
                       "{{tiempo_limite}} minutos una vez que la inicies y puedes hacerlo hasta el {{fecha_limite}}.\n\n"
                       "{{enlace_prueba}}\n\n¡Mucho éxito!\nEquipo de Talento · {{empresa}}"),
}

COMPETENCIAS = [("Conocimiento técnico", "Dominio de las herramientas y conceptos del puesto"),
                ("Resolución de problemas", "Estructura, análisis y creatividad ante un reto"),
                ("Comunicación", "Claridad al explicar ideas y escuchar"),
                ("Trabajo en equipo", "Colaboración, apertura al feedback"),
                ("Alineación cultural", "Valores y forma de trabajo compatibles"),
                ("Potencial de crecimiento", "Capacidad y ganas de aprender")]

VACANTES = [
    dict(titulo="Desarrollador/a Backend Python", departamento="Ingeniería", ubicacion="Ciudad de México",
         modalidad="hibrido", experiencia_min_anios=3, salario_min=45000, salario_max=60000, moneda="MXN",
         descripcion="Buscamos una persona que diseñe y mantenga APIs de alto tráfico para nuestra plataforma de pagos.",
         requisitos="3+ años construyendo servicios web. Experiencia con bases de datos relacionales y pruebas automatizadas.",
         obligatorias=["Python", "FastAPI", "PostgreSQL", "Docker", "Git"], deseables=["AWS", "Redis", "Kubernetes", "CI/CD"],
         dias=120),
    dict(titulo="Desarrollador/a Frontend React", departamento="Ingeniería", ubicacion="Remoto LATAM",
         modalidad="remoto", experiencia_min_anios=2, salario_min=2200, salario_max=3200, moneda="USD",
         descripcion="Construirás interfaces accesibles y rápidas para miles de comercios.",
         requisitos="Dominio de React moderno (hooks), TypeScript y CSS. Ojo para el detalle visual.",
         obligatorias=["React", "TypeScript", "JavaScript", "CSS"], deseables=["TailwindCSS", "Figma", "Cypress", "GraphQL"],
         dias=90),
    dict(titulo="Analista de Datos", departamento="Datos", ubicacion="Bogotá", modalidad="presencial",
         experiencia_min_anios=2, salario_min=6000000, salario_max=8500000, moneda="COP", mostrar_salario=False,
         descripcion="Transformarás datos en decisiones: tableros ejecutivos, análisis ad hoc y modelos simples.",
         requisitos="SQL avanzado y Python para análisis. Capacidad de comunicar hallazgos a negocio.",
         obligatorias=["SQL", "Python", "Pandas", "Power BI"], deseables=["Machine Learning", "Tableau", "Excel", "Inglés"],
         dias=75),
    dict(titulo="QA Automation Engineer", departamento="Calidad", ubicacion="Lima", modalidad="hibrido",
         experiencia_min_anios=2, salario_min=5500, salario_max=7500, moneda="PEN",
         descripcion="Liderarás la automatización de pruebas end-to-end y de API.",
         requisitos="Experiencia automatizando pruebas web y de servicios; integración en pipelines.",
         obligatorias=["Selenium", "Python", "Testing automatizado", "Postman"], deseables=["Cypress", "JMeter", "CI/CD", "Jira"],
         dias=60),
    dict(titulo="Diseñador/a UX/UI", departamento="Producto", ubicacion="Remoto", modalidad="remoto",
         experiencia_min_anios=3, salario_min=1800, salario_max=2600, moneda="USD", estado="cerrada",
         descripcion="Diseñarás experiencias simples para productos financieros complejos.",
         requisitos="Portafolio con casos de investigación y prototipado de alta fidelidad.",
         obligatorias=["Figma", "UX Research", "Prototipado"], deseables=["Adobe XD", "HTML", "CSS", "Inglés"],
         dias=160),
    dict(titulo="DevOps Engineer", departamento="Infraestructura", ubicacion="Remoto", modalidad="remoto",
         experiencia_min_anios=4, salario_min=3500, salario_max=4800, moneda="USD", estado="borrador",
         descripcion="Automatizarás nuestra infraestructura y la observabilidad de los servicios.",
         requisitos="IaC, contenedores y nubes públicas.",
         obligatorias=["Docker", "Kubernetes", "AWS", "Linux"], deseables=["Go", "CI/CD"], dias=0),
]

NOMBRES = ["Valentina Ríos", "Mateo Hernández", "Camila Torres", "Santiago Gómez", "Lucía Fernández", "Diego Martínez",
           "Sofía Ramírez", "Andrés Castillo", "Isabella Vargas", "Javier Morales", "Mariana Rojas", "Sebastián Cruz",
           "Daniela Ortiz", "Nicolás Silva", "Gabriela Mendoza", "Tomás Herrera", "Paula Jiménez", "Emilio Navarro",
           "Renata Aguilar", "Joaquín Salazar", "Ximena Paredes", "Felipe Cordero", "Antonella Ruiz", "Martín Delgado",
           "Regina Campos", "Hugo Pineda", "Elena Fuentes", "Bruno Sandoval", "Abril Montes", "Leonardo Ibarra",
           "Carla Benítez", "Iván Robles", "Natalia Quiroga", "Rodrigo Peña", "Fernanda Lozano", "Pablo Arias"]
EMPRESAS_CV = ["Fintech Andina", "Grupo Comercial del Pacífico", "Software Sur", "Banco Horizonte", "LogiData",
               "Agencia Pixel", "Telecom Norte", "Retail Express", "Salud Digital", "EduPlus"]
CARGOS = {0: "Desarrollador Backend", 1: "Desarrolladora Frontend", 2: "Analista de Datos", 3: "QA Engineer", 4: "Diseñadora UX"}
FUENTES_PESOS = [("portal_empleo", 22), ("computrabajo", 28), ("linkedin", 25), ("indeed", 10), ("referido", 10), ("evento", 5)]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _fecha_txt(meses_atras: int) -> str:
    d = AHORA.date() - timedelta(days=30 * meses_atras)
    return f"{MESES[d.month - 1].capitalize()} {d.year}"


def texto_cv(nombre: str, email: str, cargo: str, skills: list[str], anios: float, perfil_extra: str = "") -> list[tuple[str, str]]:
    """Devuelve líneas (estilo, texto) de un CV en español con secciones reconocibles."""
    meses_total = int(anios * 12)
    trabajos, cursor = [], 0
    empresas = random.sample(EMPRESAS_CV, 3)
    while meses_total > 0 and len(trabajos) < 3:
        dur = min(meses_total, random.randint(14, 40))
        fin = "Actualidad" if cursor == 0 else _fecha_txt(cursor)
        trabajos.append((f"{cargo} {'Senior' if cursor == 0 and anios > 5 else ''}".strip(), empresas[len(trabajos)],
                         f"{_fecha_txt(cursor + dur)} - {fin}"))
        cursor += dur + random.randint(0, 3)
        meses_total -= dur
    lineas = [("titulo", nombre), ("normal", f"{email} | +52 55 {random.randint(1000, 9999)} {random.randint(1000, 9999)}"),
              ("normal", f"linkedin.com/in/{normalizar(nombre).replace(' ', '-')}"),
              ("seccion", "Perfil"),
              ("normal", f"{cargo} con {anios:g} años de experiencia. {perfil_extra}Me motiva construir productos útiles "
                         f"y trabajar en equipos colaborativos."),
              ("seccion", "Experiencia")]
    for i, (puesto, emp, periodo) in enumerate(trabajos):
        uso = ", ".join(random.sample(skills, min(len(skills), 3)))
        lineas += [("negrita", f"{puesto} | {emp} | {periodo}"),
                   ("normal", f"• Desarrollé y mantuve soluciones usando {uso}."),
                   ("normal", "• Colaboré con producto y diseño en ciclos de entrega quincenales.")]
    lineas += [("seccion", "Educación"),
               ("normal", random.choice(["Ingeniería en Sistemas Computacionales · Universidad Nacional",
                                         "Licenciatura en Informática · Universidad Autónoma",
                                         "Ingeniería Industrial · Instituto Tecnológico",
                                         "Licenciatura en Diseño Digital · Universidad Iberoamericana"])),
               ("seccion", "Habilidades"), ("normal", ", ".join(skills)),
               ("seccion", "Idiomas"), ("normal", random.choice(["Español nativo, Inglés B2", "Español nativo, Inglés C1",
                                                                  "Español nativo, Inglés intermedio"]))]
    return lineas


def a_pdf(lineas) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = A4[1] - 2 * cm
    for estilo, t in lineas:
        tam = {"titulo": 18, "seccion": 13, "negrita": 11}.get(estilo, 10)
        fuente = "Helvetica-Bold" if estilo in ("titulo", "seccion", "negrita") else "Helvetica"
        if estilo == "seccion":
            y -= 8
        c.setFont(fuente, tam)
        c.drawString(2 * cm, y, t[:110])
        y -= tam + 5
    c.save()
    return buf.getvalue()


def a_docx(lineas) -> bytes:
    d = DocxDocument()
    for estilo, t in lineas:
        if estilo == "titulo":
            d.add_heading(t, level=0)
        elif estilo == "seccion":
            d.add_heading(t, level=1)
        else:
            p = d.add_paragraph()
            p.add_run(t).bold = estilo == "negrita"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _skills_para(v: dict, calidad: float) -> list[str]:
    """Habilidades de un candidato: toma de la vacante según `calidad` y añade ruido."""
    obl = [s for s in v["obligatorias"] if random.random() < calidad + 0.15]
    des = [s for s in v["deseables"] if random.random() < calidad - 0.1]
    ruido = random.sample([s for s in HABILIDADES["tecnica"] if s not in v["obligatorias"] + v["deseables"]], 3)
    skills = obl + des + ruido + random.sample(["Trabajo en equipo", "Comunicación efectiva", "Inglés", "Scrum"], 2)
    random.shuffle(skills)
    # En los CV la gente escribe sinónimos: el normalizador debe resolverlos.
    alias = {"JavaScript": "JS", "PostgreSQL": "Postgres", "Node.js": "NodeJS", "Kubernetes": "K8s", "React": "ReactJS"}
    return [alias[s] if s in alias and random.random() < 0.5 else s for s in skills]


def limpiar(db) -> None:
    tablas = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'etapas'")).scalars().all()
    db.execute(text(f"TRUNCATE {', '.join(tablas)} RESTART IDENTITY CASCADE"))
    if settings.upload_dir.exists():
        for f in settings.upload_dir.iterdir():
            if f.is_file():
                f.unlink()
    db.commit()
    invalidar_indice()


def main() -> None:
    db = SessionLocal()
    limpiar(db)

    emp = Empresa(nombre="Nébula Tech", slug="nebula-tech", color_marca="#4f46e5", sitio_web="https://nebula.example",
                  descripcion="Construimos software financiero para que los pequeños comercios de Latinoamérica crezcan. "
                              "Equipo distribuido en 6 países, cultura de aprendizaje y trabajo flexible.")
    db.add(emp)
    db.flush()
    pw = hash_password("Demo1234!")
    usuarios = {
        "admin": Usuario(empresa_id=emp.id, nombre="Anggie Alcedo", email="admin@talentflow.demo", password_hash=pw, rol="admin"),
        "reclu": Usuario(empresa_id=emp.id, nombre="Laura Méndez", email="reclutadora@talentflow.demo", password_hash=pw, rol="reclutador"),
        "ent1": Usuario(empresa_id=emp.id, nombre="Carlos Rivas", email="carlos@talentflow.demo", password_hash=pw, rol="entrevistador"),
        "ent2": Usuario(empresa_id=emp.id, nombre="Mónica Salas", email="monica@talentflow.demo", password_hash=pw, rol="entrevistador"),
    }
    db.add_all(usuarios.values())

    for cat, habs in HABILIDADES.items():
        for nombre, sinonimos in habs.items():
            h = Habilidad(nombre=nombre, categoria=cat)
            db.add(h)
            db.flush()
            for s in {normalizar(nombre), *(normalizar(x) for x in sinonimos)}:
                db.add(HabilidadSinonimo(habilidad_id=h.id, sinonimo=s))
    db.add_all(Competencia(nombre=n, descripcion=d) for n, d in COMPETENCIAS)
    db.add_all(PlantillaCorreo(codigo=c, nombre=n, asunto=a, cuerpo=b) for c, (n, a, b) in PLANTILLAS.items())
    db.flush()
    invalidar_indice()
    por_nombre = {h.nombre: h for h in db.scalars(select(Habilidad))}

    vacantes = []
    for i, d in enumerate(VACANTES):
        v = Vacante(empresa_id=emp.id, reclutador_id=usuarios["reclu" if i % 2 else "admin"].id, titulo=d["titulo"],
                    slug=normalizar(d["titulo"]).replace("/", "-").replace(" ", "-"), departamento=d["departamento"],
                    ubicacion=d["ubicacion"], modalidad=d["modalidad"], descripcion=d["descripcion"],
                    requisitos=d["requisitos"], experiencia_min_anios=d["experiencia_min_anios"],
                    salario_min=d["salario_min"], salario_max=d["salario_max"], moneda=d["moneda"],
                    mostrar_salario=d.get("mostrar_salario", True), estado="publicada",
                    publicada_en=AHORA - timedelta(days=d["dias"]))
        v.habilidades = ([VacanteHabilidad(habilidad_id=por_nombre[s].id, tipo="obligatoria") for s in d["obligatorias"]]
                         + [VacanteHabilidad(habilidad_id=por_nombre[s].id, tipo="deseable") for s in d["deseables"]])
        db.add(v)
        vacantes.append((v, d))
    db.flush()

    # ------------------------------------------------------------ candidatos
    nombres = iter(NOMBRES)
    fuentes = [f for f, _ in FUENTES_PESOS]
    pesos = [p for _, p in FUENTES_PESOS]
    postulaciones = []
    for idx, (v, d) in enumerate(vacantes[:5]):
        n_cand = {0: 9, 1: 8, 2: 7, 3: 6, 4: 6}[idx]
        for k in range(n_cand):
            nombre = next(nombres, None) or f"Candidato {idx}-{k}"
            email = normalizar(nombre).replace(" ", ".") + "@correo.example"
            calidad = random.uniform(0.35, 0.95)
            anios = round(random.uniform(max(0.5, d["experiencia_min_anios"] - 1.5), d["experiencia_min_anios"] + 4) * 2) / 2
            lineas = texto_cv(nombre, email, CARGOS[idx], _skills_para(d, calidad), anios)
            es_pdf = k % 3 != 2
            fuente = random.choices(fuentes, pesos)[0]
            p = crear_postulacion(db, vacante=v, nombre=nombre, email=email, telefono=None, linkedin=None,
                                  fuente=fuente, carta="Me entusiasma el reto y la misión de la empresa." if k % 2 else None,
                                  archivo_nombre=f"CV_{nombre.split()[0]}.{'pdf' if es_pdf else 'docx'}",
                                  archivo=a_pdf(lineas) if es_pdf else a_docx(lineas), consentimiento=True, ip="127.0.0.1")
            postulaciones.append((p, d, calidad, fuente))
    db.flush()

    # ---------------------------------------------- movimientos en el pipeline
    flujo = ["revision", "entrevista_tecnica", "entrevista_rh", "oferta", "contratado"]
    reclu = usuarios["reclu"]
    # Por vacante se ordena a los candidatos por match (+ bonus a referidos, + ruido) y
    # el ranking decide hasta dónde llegó cada quien: embudo realista, 1 contratación por vacante madura.
    planes = {}
    for d in VACANTES[:5]:
        grupo = [x for x in postulaciones if x[1] is d]
        grupo.sort(key=lambda x: -(float(x[0].match_score) + (12 if x[3] == "referido" else 0) + random.uniform(-10, 10)))
        cerrada, madura = d.get("estado") == "cerrada", d["dias"] >= 75
        avance = [5, 4, 3, 2] if madura else [4, 3, 2, 2]
        for rank, x in enumerate(grupo):
            if cerrada:
                planes[x[0].id] = (5, False) if rank == 0 else (random.choice([1, 2, 3]), True)
            elif rank < 4:
                planes[x[0].id] = (avance[rank], False)
            else:
                r = random.random()
                planes[x[0].id] = (random.choice([1, 2]), True) if r < 0.45 else (1, False) if r < 0.75 else (0, False)

    for p, d, calidad, fuente in postulaciones:
        objetivo, descartar = planes[p.id]
        dias_min = 3 + objetivo * 8
        inicio = AHORA - timedelta(days=random.randint(dias_min, max(dias_min + 1, d["dias"] - 3)))
        t = inicio
        for codigo in flujo[:objetivo]:
            t += timedelta(days=random.randint(2, 9))
            mover_etapa(db, p, codigo, reclu.id, notificar=False)
            p.historial[-1].creado_en = min(t, AHORA - timedelta(hours=1))
        if descartar:
            t += timedelta(days=random.randint(1, 5))
            mover_etapa(db, p, "descartado", reclu.id, comentario="Perfil con menor ajuste a requisitos obligatorios",
                        notificar=objetivo > 0)
            p.historial[-1].creado_en = min(t, AHORA - timedelta(hours=1))
        p.creada_en = inicio
        p.historial[0].creado_en = inicio
        if p.contratado_en:
            p.contratado_en = p.historial[-1].creado_en
        p.actualizada_en = p.historial[-1].creado_en
    db.flush()
    for v, d in vacantes:
        if d.get("estado"):
            v.estado = d["estado"]
            v.cerrada_en = AHORA - timedelta(days=10) if d["estado"] == "cerrada" else None
            v.publicada_en = None if d["estado"] == "borrador" else v.publicada_en

    # -------------------------------------------------- entrevistas + evaluaciones
    competencias = db.scalars(select(Competencia)).all()
    for p, d, calidad, _ in postulaciones:
        alcanzo = max((h.etapa_hasta.orden for h in p.historial if h.etapa_hasta.codigo != "descartado"), default=1)
        for tipo, orden, ent in (("tecnica", 3, usuarios["ent1"]), ("rh", 4, usuarios["ent2"])):
            if alcanzo < orden:
                continue
            momento = next(h.creado_en for h in p.historial if h.etapa_hasta.orden == orden)
            futura = p.etapa.orden == orden and random.random() < 0.6
            inicio = (AHORA + timedelta(days=random.randint(1, 6), hours=random.randint(0, 6))) if futura \
                else momento + timedelta(days=2)
            inicio = inicio.replace(minute=0, second=0, microsecond=0, hour=random.choice([15, 16, 17, 18, 21]))
            e = Entrevista(postulacion_id=p.id, tipo=tipo, inicio=inicio, duracion_min=60 if tipo == "tecnica" else 45,
                           lugar="https://meet.example/" + token_aleatorio()[:10], uid_ics=f"{token_aleatorio()[:20]}@talentflow",
                           estado="programada" if futura else "realizada", creado_por=reclu.id, entrevistadores=[ent])
            db.add(e)
            db.flush()
            if not futura:
                base = 2 + calidad * 3
                ev = Evaluacion(entrevista_id=e.id, evaluador_id=ent.id,
                                recomendacion="fuerte_si" if base > 4.3 else "si" if base > 3.4 else "no",
                                fortalezas="Buena estructura al resolver el ejercicio y comunicación clara.",
                                areas_mejora="Profundizar en diseño de sistemas y pruebas.")
                ev.puntajes = [EvaluacionPuntaje(competencia_id=c.id, puntaje=max(1, min(5, round(base + random.uniform(-1, 1)))))
                               for c in competencias]
                db.add(ev)

    # ------------------------------------------------------------- prueba técnica
    prueba = Prueba(empresa_id=emp.id, titulo="Python Backend · Nivel intermedio", tiempo_limite_min=40, puntaje_aprobacion=60,
                    descripcion="4 preguntas de opción múltiple y 2 ejercicios de código. Puedes usar la documentación oficial.")
    prueba.preguntas = [
        PruebaPregunta(orden=1, tipo="opcion_multiple", puntos=10, enunciado="¿Qué tipo de índice usa PostgreSQL para búsquedas full-text sobre tsvector?",
                       opciones=["B-tree", "GIN", "Hash", "BRIN"], respuesta_correcta=1),
        PruebaPregunta(orden=2, tipo="opcion_multiple", puntos=10, enunciado="¿Qué código HTTP corresponde a «recurso creado»?",
                       opciones=["200", "201", "204", "302"], respuesta_correcta=1),
        PruebaPregunta(orden=3, tipo="opcion_multiple", puntos=10, enunciado="En Python, ¿qué devuelve `[x*2 for x in range(3)]`?",
                       opciones=["[0, 2, 4]", "[2, 4, 6]", "(0, 2, 4)", "Error"], respuesta_correcta=0),
        PruebaPregunta(orden=4, tipo="opcion_multiple", puntos=10, enunciado="¿Qué nivel de aislamiento evita lecturas no repetibles?",
                       opciones=["Read uncommitted", "Read committed", "Repeatable read", "Ninguno"], respuesta_correcta=2),
        PruebaPregunta(orden=5, tipo="codigo", puntos=30, funcion="es_palindromo",
                       enunciado="Implementa `es_palindromo(texto)` que devuelva True si el texto es palíndromo ignorando mayúsculas, espacios y signos.",
                       plantilla_codigo="def es_palindromo(texto):\n    # tu código aquí\n    pass\n",
                       casos_prueba=[{"entrada": ["Anita lava la tina"], "esperado": True},
                                     {"entrada": ["Python"], "esperado": False},
                                     {"entrada": ["¿Acaso hubo búhos acá?"], "esperado": True},
                                     {"entrada": [""], "esperado": True}]),
        PruebaPregunta(orden=6, tipo="codigo", puntos=30, funcion="top_habilidades",
                       enunciado="Implementa `top_habilidades(lista, n)` que reciba una lista de habilidades (con repetidos) y devuelva las n más frecuentes, desempatando alfabéticamente.",
                       plantilla_codigo="def top_habilidades(lista, n):\n    pass\n",
                       casos_prueba=[{"entrada": [["python", "sql", "python", "go", "sql", "python"], 2], "esperado": ["python", "sql"]},
                                     {"entrada": [["b", "a", "c"], 2], "esperado": ["a", "b"]},
                                     {"entrada": [[], 3], "esperado": []}]),
    ]
    db.add(prueba)
    db.flush()
    buena = ("def es_palindromo(texto):\n    limpio = [c for c in texto.lower() if c.isalnum()]\n"
             "    tabla = str.maketrans('áéíóúü', 'aeiouu')\n    limpio = ''.join(limpio).translate(tabla)\n"
             "    return limpio == limpio[::-1]\n")
    top = ("from collections import Counter\ndef top_habilidades(lista, n):\n"
           "    return [h for h, _ in sorted(Counter(lista).items(), key=lambda kv: (-kv[1], kv[0]))[:n]]\n")
    backend = [x for x in postulaciones if x[1] is VACANTES[0] and x[0].etapa.orden >= 3 and x[0].etapa.codigo != "descartado"]
    for j, (p, _, calidad, _) in enumerate(backend[:3]):
        a = PruebaAsignacion(prueba_id=prueba.id, postulacion_id=p.id, token=token_aleatorio(),
                             enviada_en=AHORA - timedelta(days=6), expira_en=AHORA + timedelta(days=2 if j == 2 else -1))
        db.add(a)
        if j == 2:
            continue   # pendiente: el candidato aún no la responde
        a.iniciada_en = AHORA - timedelta(days=4)
        respuestas = {1: {"opcion": 1}, 2: {"opcion": 1}, 3: {"opcion": 0 if calidad > 0.5 else 1}, 4: {"opcion": 2 if j == 0 else 1},
                      5: {"codigo": buena if j == 0 else "def es_palindromo(texto):\n    return texto == texto[::-1]\n"},
                      6: {"codigo": top}}
        total = maximo = 0
        for q in prueba.preguntas:
            pts, det = calificador.calificar_pregunta(q, respuestas[q.orden])
            a.respuestas.append(PruebaRespuesta(pregunta_id=q.id, respuesta=respuestas[q.orden], puntos_obtenidos=pts, detalle=det))
            total += pts
            maximo += q.puntos
        a.puntaje, a.puntaje_max, a.completada_en = total, maximo, AHORA - timedelta(days=4, hours=-1)

    # --------------------------------------------------------------- privacidad
    vencido = postulaciones[-1][0].candidato
    vencido.retener_hasta = date.today() - timedelta(days=3)
    solicitante = postulaciones[-2][0].candidato
    db.add(SolicitudPrivacidad(candidato_id=solicitante.id, email_hash=hash_email(solicitante.email), tipo="borrado",
                               motivo="Ya encontré empleo y prefiero que no conserven mis datos."))

    # ------------------------------------------------------- modo uso personal
    yo = usuarios["admin"]
    mis_skills = ["Python", "Selenium", "Pytest", "Postman", "Figma", "WordPress", "HTML", "CSS", "JavaScript", "SQL",
                  "PostgreSQL", "Git", "Jira", "Scrum", "Testing automatizado", "Comunicación efectiva", "Trabajo en equipo"]
    lineas = texto_cv("Anggie Alcedo", "anggie@correo.example", "QA Engineer y Diseñadora UI", mis_skills, 4,
                      "Combino automatización de pruebas con diseño de interfaces. ")
    _, texto, datos, _ = procesar_cv(db, "CV_Anggie_Alcedo.pdf", a_pdf(lineas))
    db.add(MiCV(usuario_id=yo.id, nombre_original="CV_Anggie_Alcedo.pdf", texto=texto, datos=datos))
    db.flush()
    from app.routers.personal import _analizar
    mi_cv = db.get(MiCV, yo.id)
    hoy = date.today()
    mias = [
        ("Globant", "QA Automation Engineer", "en_proceso", -12, "remoto",
         "Requisitos:\n- 3+ años en automatización de pruebas\n- Selenium o Cypress con Python o JavaScript\n- Pruebas de API con Postman\n"
         "- Integración en CI/CD\nDeseable:\n- JMeter para pruebas de carga\n- Experiencia con Docker"),
        ("Mercado Libre", "UX/UI Designer", "entrevista", -20, "hibrido",
         "Buscamos diseñadora con 3 años de experiencia en Figma, UX Research y prototipado. Se valora conocimiento de HTML y CSS. Inglés avanzado."),
        ("Rappi", "Frontend Developer", "postulada", -5, "remoto",
         "React, TypeScript, TailwindCSS y testing con Cypress. 2+ años. Plus: GraphQL."),
        ("Agencia Creativa Lima", "Desarrolladora WordPress", "oferta", -30, "presencial",
         "WordPress, PHP, HTML, CSS y JavaScript. Deseable Figma. 2 años de experiencia."),
        ("Banco Digital", "QA Analyst", "sin_respuesta", -40, "hibrido",
         "Pruebas funcionales y automatizadas. SQL, Jira, Scrum. Deseable: Selenium, Java. 2 años."),
        ("Startup Salud", "QA Lead", "por_postular", None, "remoto",
         "5+ años en QA. Liderazgo de equipo, Selenium, Pytest, CI/CD, Docker y AWS. Inglés C1."),
    ]
    for empresa, puesto, estado, delta, modalidad, desc in mias:
        fp = hoy + timedelta(days=delta) if delta is not None else None
        mp = MiPostulacion(usuario_id=yo.id, empresa=empresa, puesto=puesto, estado=estado, modalidad=modalidad,
                           descripcion=desc, fecha_postulacion=fp, url=f"https://empleos.example/{normalizar(puesto).replace(' ', '-')}",
                           proximo_seguimiento=(fp + timedelta(days=7 if estado != "sin_respuesta" else 10)) if fp else None,
                           contacto="Reclutadora: Ana P." if estado in ("entrevista", "oferta", "en_proceso") else None,
                           notas="Preparar portafolio con casos de QA y diseño." if estado == "entrevista" else None)
        _analizar(db, mp, mi_cv)
        db.add(mp)
        db.flush()
        if mp.proximo_seguimiento:
            mp.recordatorios.append(MiRecordatorio(fecha=mp.proximo_seguimiento, texto=f"Dar seguimiento a {empresa}"))
        if estado == "entrevista":
            mp.recordatorios.append(MiRecordatorio(fecha=hoy + timedelta(days=2), texto="Entrevista con el equipo de diseño (preparar caso)"))

    db.commit()
    total = db.execute(text("SELECT (SELECT count(*) FROM candidatos), (SELECT count(*) FROM postulaciones), "
                            "(SELECT count(*) FROM entrevistas), (SELECT count(*) FROM correos)")).one()
    print(f"Seed listo · candidatos={total[0]} postulaciones={total[1]} entrevistas={total[2]} correos={total[3]}")
    print("Usuarios (contraseña Demo1234!): admin@ · reclutadora@ · carlos@ · monica@talentflow.demo")
    db.close()


if __name__ == "__main__":
    main()
