"""Dependencias de FastAPI para autenticacion."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.modelos.usuario import Usuario
from app.seguridad.jwt import decodificar_token_acceso
from app.utilidades.respuestas import error_autenticacion

esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


def obtener_usuario_actual(
    token: str = Depends(esquema_oauth2),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    """Resuelve el usuario autenticado a partir del token JWT (HTTP 401 si no es valido)."""

    contenido = decodificar_token_acceso(token)
    if contenido is None:
        raise error_autenticacion("El token de acceso es invalido o ha expirado.")

    # El `sub` del token es el id del usuario.
    sub = contenido.get("sub")
    try:
        usuario_id = int(sub)
    except (TypeError, ValueError):
        raise error_autenticacion("El token de acceso no es valido.")

    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise error_autenticacion("El usuario no existe o se encuentra inactivo.")

    return usuario
