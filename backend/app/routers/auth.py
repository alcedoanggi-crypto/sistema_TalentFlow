from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_actual
from app.models import Usuario
from app.schemas import LoginIn
from app.security import crear_token, verificar_password

router = APIRouter(prefix="/api", tags=["auth"])


def _usuario(u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol,
            "empresa": {"id": u.empresa.id, "nombre": u.empresa.nombre, "slug": u.empresa.slug,
                        "color": u.empresa.color_marca}}


@router.post("/auth/login")
def login(datos: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(Usuario).where(Usuario.email == datos.email.lower()))
    if u is None or not u.activo or not verificar_password(datos.password, u.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return {"token": crear_token(u.id, u.rol), "usuario": _usuario(u)}


@router.get("/auth/yo")
def yo(u: Usuario = Depends(usuario_actual)):
    return _usuario(u)


@router.get("/usuarios")
def usuarios(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    filas = db.scalars(select(Usuario).where(Usuario.empresa_id == u.empresa_id, Usuario.activo)
                       .order_by(Usuario.nombre))
    return [{"id": x.id, "nombre": x.nombre, "rol": x.rol, "email": x.email} for x in filas]
