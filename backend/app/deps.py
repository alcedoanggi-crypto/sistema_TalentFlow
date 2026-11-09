from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.security import decodificar_token

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                   db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión para continuar")
    try:
        payload = decodificar_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")
    return usuario


def requiere(*roles: str) -> Callable[..., Usuario]:
    def _dep(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return usuario
    return _dep


GESTION = ("admin", "reclutador")


def obtener(db: Session, modelo, pk, empresa_id: int | None = None):
    """db.get con 404; si se indica empresa_id, verifica que el registro sea de esa empresa."""
    obj = db.get(modelo, pk)
    if obj is None or (empresa_id is not None and getattr(obj, "empresa_id", empresa_id) != empresa_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{modelo.__name__} no encontrado")
    return obj
