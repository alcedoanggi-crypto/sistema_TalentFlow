import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def crear_token(usuario_id: int, rol: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expira_minutos)
    payload = {"sub": str(usuario_id), "rol": rol, "exp": expira}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo])


def token_aleatorio() -> str:
    """Token opaco para enlaces sin contraseña (portal del candidato, pruebas)."""
    return secrets.token_urlsafe(32)


def hash_email(email: str) -> str:
    """Huella irreversible del correo: permite probar que se atendió una solicitud
    de borrado sin conservar el dato personal."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()
