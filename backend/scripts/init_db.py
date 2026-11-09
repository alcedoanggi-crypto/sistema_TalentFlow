"""Aplica los archivos de sql/ en orden. Idempotente (CREATE ... IF NOT EXISTS / OR REPLACE).

Uso:  python -m scripts.init_db
Antes, como superusuario:  psql -U postgres -h localhost -f scripts/crear_bd.sql
"""
from pathlib import Path

from sqlalchemy import text

from app.database import engine

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def main() -> None:
    with engine.begin() as con:
        for archivo in sorted(SQL_DIR.glob("*.sql")):
            print(f"-> {archivo.name}")
            con.exec_driver_sql(archivo.read_text(encoding="utf-8"))
        tablas = con.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")).scalar()
    print(f"Esquema listo: {tablas} tablas.")


if __name__ == "__main__":
    main()
