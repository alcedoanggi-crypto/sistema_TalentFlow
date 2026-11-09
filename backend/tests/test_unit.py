from datetime import date, datetime, timezone

from app.services import calificador
from app.services.cv_parser import analizar, anios_de_experiencia, rangos_de_fechas, segmentar, validar_archivo, CVInvalido
from app.services.habilidades import normalizar
from app.services.ics import generar_ics
from app.services.matching import Requisito, calcular_match

import pytest


# ------------------------------------------------------------- matching
def test_match_pondera_obligatorias_deseables_y_experiencia():
    reqs = [Requisito(1, "Python", "obligatoria"), Requisito(2, "SQL", "obligatoria"), Requisito(3, "AWS", "deseable")]
    d = calcular_match({1: "Python", 9: "Figma"}, 1.5, reqs, 3)
    # 60·(1/2) + 25·0 + 15·(1.5/3) = 37.5
    assert d["score"] == 37.5
    assert d["obligatorias"] == {"cumple": ["Python"], "faltan": ["SQL"]}
    assert d["adicionales"] == ["Figma"]
    assert d["experiencia"]["cumple"] is False


def test_match_redistribuye_peso_sin_deseables():
    d = calcular_match({1: "Python"}, 5, [Requisito(1, "Python", "obligatoria")], 2)
    assert d["score"] == 100.0
    assert "deseables" not in d["pesos"]


# ------------------------------------------------------------- CV parser
def test_normalizar_quita_tildes_y_espacios():
    assert normalizar("  Programación   JS ") == "programacion js"


def test_rangos_y_solapamientos():
    texto = "Dev | Acme | Ene 2020 - Dic 2021\nFreelance 2021 - 2022\nLead | Foo | mar 2023 - actualidad"
    rangos = rangos_de_fechas(texto, hoy=date(2024, 3, 1))
    assert len(rangos) == 3
    # 2020-01..2022-12 fusionado (35 meses) + 2023-03..2024-03 (12) = 47 meses ≈ 4 años
    assert anios_de_experiencia(rangos) == 4.0


def test_segmentar_y_analizar_por_reglas():
    texto = ("MARÍA PÉREZ\nmaria.perez@mail.com | +52 55 1234 5678\nExperiencia\n"
             "Backend Developer | Acme | Ene 2019 - Dic 2022\nEducación\nIngeniería en Sistemas · UNAM\nHabilidades\nPython, SQL")
    sec = segmentar(texto)
    assert {"experiencia", "educacion", "habilidades"} <= set(sec)
    datos = analizar(texto, hoy=date(2024, 1, 1))
    assert datos["email"] == "maria.perez@mail.com"
    assert datos["nombre"] == "María Pérez"
    assert datos["experiencia_anios"] == 4.0
    assert datos["telefono"]


def test_validar_archivo_rechaza_extension_falsa():
    with pytest.raises(CVInvalido):
        validar_archivo("cv.pdf", b"PK\x03\x04 esto es un zip")
    with pytest.raises(CVInvalido):
        validar_archivo("cv.doc", b"cualquiera")
    assert validar_archivo("cv.pdf", b"%PDF-1.7...") == "application/pdf"


# ------------------------------------------------------------- calificador
def test_codigo_correcto_y_credito_parcial():
    casos = [{"entrada": [2, 3], "esperado": 5}, {"entrada": [0, 0], "esperado": 0}, {"entrada": [-1, 1], "esperado": 1}]
    r = calificador.ejecutar_codigo("def suma(a, b):\n    return a + b\n", "suma", casos)
    assert [c["ok"] for c in r["casos"]] == [True, True, False]


@pytest.mark.parametrize("codigo,mensaje", [
    ("import os\ndef f(): return os.listdir('.')", "Import no permitido"),
    ("def f(): return open('x').read()", "Uso no permitido"),
    ("def f(): return ().__class__.__bases__", "atributos internos"),
])
def test_codigo_peligroso_bloqueado(codigo, mensaje):
    with pytest.raises(calificador.CodigoNoPermitido, match=mensaje):
        calificador.validar_codigo(codigo)


def test_bucle_infinito_corta_por_tiempo():
    r = calificador.ejecutar_codigo("def f():\n    while True: pass\n", "f", [{"entrada": [], "esperado": 1}])
    assert "Tiempo límite" in r["error"]


# ------------------------------------------------------------- ics
def test_ics_estructura_y_plegado():
    ics = generar_ics(uid="abc@tf", secuencia=2, inicio=datetime(2025, 1, 10, 15, tzinfo=timezone.utc), duracion_min=45,
                      titulo="Entrevista técnica · Backend, Python", descripcion="Línea 1\nLínea 2 " + "x" * 120,
                      lugar="https://meet.example/abc", organizador=("Ana", "ana@x.com"),
                      asistentes=[("Luis", "luis@x.com")])
    assert "DTSTART:20250110T150000Z" in ics and "DTEND:20250110T154500Z" in ics
    assert "SEQUENCE:2" in ics and "METHOD:REQUEST" in ics
    assert "Backend\\, Python" in ics and "Línea 1\\nLínea 2" in ics
    assert all(len(l.encode()) <= 75 for l in ics.split("\r\n"))
    cancel = generar_ics(uid="abc@tf", secuencia=3, inicio=datetime(2025, 1, 10, 15, tzinfo=timezone.utc), duracion_min=45,
                         titulo="x", descripcion="", lugar=None, organizador=("A", "a@x.com"), asistentes=[], cancelar=True)
    assert "METHOD:CANCEL" in cancel and "STATUS:CANCELLED" in cancel
