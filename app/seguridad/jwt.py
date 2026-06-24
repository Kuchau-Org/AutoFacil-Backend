"""Generacion y verificacion de tokens JWT de autenticacion."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.config import obtener_configuracion

configuracion = obtener_configuracion()


def crear_token_acceso(subject: str) -> str:
    """Genera un token JWT de acceso firmado con el id del usuario."""

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(minutes=configuracion.minutos_expiracion_token)
    contenido = {
        "sub": subject,
        "tipo": "acceso",
        "iat": ahora,
        "exp": expiracion,
    }
    return jwt.encode(
        contenido, configuracion.clave_secreta, algorithm=configuracion.algoritmo_jwt
    )


def decodificar_token_acceso(token: str) -> dict | None:
    """Decodifica un token de acceso; devuelve su contenido o None si no es valido."""

    try:
        contenido = jwt.decode(
            token,
            configuracion.clave_secreta,
            algorithms=[configuracion.algoritmo_jwt],
        )
    except InvalidTokenError:
        return None
    if contenido.get("tipo") != "acceso":
        return None
    return contenido
