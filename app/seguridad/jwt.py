"""Generacion y verificacion de tokens JWT de autenticacion."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.config import obtener_configuracion

configuracion = obtener_configuracion()


def crear_token_acceso(subject: str) -> str:
    """Genera un token JWT de acceso firmado con el id del usuario.

    El campo `sub` contiene el id del usuario; `exp` define la expiracion segun
    la configuracion de la aplicacion.
    """

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(minutes=configuracion.minutos_expiracion_token)
    contenido = {
        "sub": subject,
        # tipo="acceso": los endpoints privados rechazan tokens de otro tipo.
        "tipo": "acceso",
        "iat": ahora,
        "exp": expiracion,
    }
    return jwt.encode(
        contenido, configuracion.clave_secreta, algorithm=configuracion.algoritmo_jwt
    )


def decodificar_token_acceso(token: str) -> dict | None:
    """Decodifica un token de ACCESO; devuelve su contenido o `None` si no es valido.

    Solo acepta tokens cuyo claim `tipo` sea exactamente "acceso"; cualquier otro
    token se rechaza para que no sirva como credencial.
    """

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
