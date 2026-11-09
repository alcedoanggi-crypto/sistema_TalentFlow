"""Calificación automática de pruebas técnicas.

Opción múltiple: comparación directa con el índice correcto.

Código (Python): el candidato implementa una función que se ejecuta contra los
casos de prueba. Defensa en capas:
  1. Análisis AST: solo se permiten imports de una lista blanca y se bloquean
     open/exec/eval/__import__ y el acceso a atributos "dunder" (__class__,
     __subclasses__...), la vía clásica para escapar de un sandbox.
  2. Proceso hijo aislado (`python -I`, entorno vacío, directorio temporal)
     con __builtins__ reducido y tiempo límite.
Esto basta para un portafolio/demo. En producción el código ajeno debe correr
en un contenedor efímero sin red (gVisor, Firecracker, Judge0...).
"""
import ast
import os
import json
import subprocess
import sys
import tempfile
from decimal import Decimal

from app.config import settings

MODULOS_PERMITIDOS = {"math", "itertools", "collections", "functools", "re", "string", "heapq", "bisect",
                      "statistics", "operator"}
NOMBRES_PROHIBIDOS = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
                      "getattr", "setattr", "delattr", "input", "breakpoint", "memoryview", "help", "exit", "quit"}


class CodigoNoPermitido(ValueError):
    pass


def validar_codigo(codigo: str) -> None:
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as exc:
        raise CodigoNoPermitido(f"Error de sintaxis en la línea {exc.lineno}: {exc.msg}") from exc
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name.split(".")[0] not in MODULOS_PERMITIDOS:
                    raise CodigoNoPermitido(f"Import no permitido: {alias.name}")
        elif isinstance(nodo, ast.ImportFrom):
            if (nodo.module or "").split(".")[0] not in MODULOS_PERMITIDOS:
                raise CodigoNoPermitido(f"Import no permitido: {nodo.module}")
        elif isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PROHIBIDOS:
            raise CodigoNoPermitido(f"Uso no permitido: {nodo.id}")
        elif isinstance(nodo, ast.Attribute) and nodo.attr.startswith("__"):
            raise CodigoNoPermitido("No se permite acceder a atributos internos (__...__)")


# Se ejecuta dentro del proceso hijo. Recibe JSON por stdin y responde JSON por stdout.
_EJECUTOR = r'''
import builtins, json, sys
datos = json.loads(sys.stdin.read())
permitidos = set(datos["modulos"])
_imp = builtins.__import__
def _import_seguro(nombre, *a, **k):
    if nombre.split(".")[0] not in permitidos:
        raise ImportError("import no permitido: " + nombre)
    return _imp(nombre, *a, **k)
seguros = {n: getattr(builtins, n) for n in dir(builtins) if n not in set(datos["prohibidos"]) and not n.startswith("_")}
seguros["__import__"] = _import_seguro
seguros["__build_class__"] = builtins.__build_class__
seguros["__name__"] = "candidato"
entorno = {"__builtins__": seguros}
salida = []
try:
    exec(compile(datos["codigo"], "<candidato>", "exec"), entorno)
    funcion = entorno[datos["funcion"]]
except Exception as exc:
    print(json.dumps({"error": f"{type(exc).__name__}: {exc}"})); sys.exit(0)
for caso in datos["casos"]:
    try:
        obtenido = funcion(*caso["entrada"])
        if isinstance(obtenido, tuple): obtenido = list(obtenido)
        salida.append({"ok": obtenido == caso["esperado"], "obtenido": repr(obtenido)[:200]})
    except Exception as exc:
        salida.append({"ok": False, "obtenido": f"{type(exc).__name__}: {exc}"[:200]})
print(json.dumps({"casos": salida}))
'''


def ejecutar_codigo(codigo: str, funcion: str, casos: list[dict]) -> dict:
    validar_codigo(codigo)
    entrada = json.dumps({"codigo": codigo, "funcion": funcion, "casos": casos,
                          "modulos": sorted(MODULOS_PERMITIDOS), "prohibidos": sorted(NOMBRES_PROHIBIDOS)})
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run([sys.executable, "-I", "-S", "-c", _EJECUTOR], input=entrada, cwd=tmp,
                                  capture_output=True, text=True, timeout=settings.prueba_codigo_timeout_s,
                                  env={"SYSTEMROOT": os.environ.get("SYSTEMROOT", "")})
        except subprocess.TimeoutExpired:
            return {"error": f"Tiempo límite excedido ({settings.prueba_codigo_timeout_s:g} s). ¿Bucle infinito?"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": (proc.stderr or "Sin salida")[-300:]}


def calificar_pregunta(pregunta, respuesta: dict) -> tuple[Decimal, dict]:
    """Devuelve (puntos_obtenidos, detalle). `pregunta` es un PruebaPregunta."""
    puntos = Decimal(pregunta.puntos)
    if pregunta.tipo == "opcion_multiple":
        elegida = respuesta.get("opcion")
        correcta = elegida is not None and int(elegida) == pregunta.respuesta_correcta
        return (puntos if correcta else Decimal(0)), {"correcta": correcta}

    codigo = respuesta.get("codigo") or ""
    if not codigo.strip():
        return Decimal(0), {"error": "Sin respuesta"}
    try:
        resultado = ejecutar_codigo(codigo, pregunta.funcion, pregunta.casos_prueba or [])
    except CodigoNoPermitido as exc:
        return Decimal(0), {"error": str(exc)}
    if "error" in resultado:
        return Decimal(0), resultado
    casos = resultado["casos"]
    aprobados = sum(1 for c in casos if c["ok"])
    # Crédito parcial proporcional a los casos superados.
    obtenidos = (puntos * aprobados / len(casos)).quantize(Decimal("0.01")) if casos else Decimal(0)
    return obtenidos, {"aprobados": aprobados, "total": len(casos), "casos": casos}
