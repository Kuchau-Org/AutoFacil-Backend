"""Generacion y verificacion de tokens JWT de autenticacion."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

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

    Solo acepta tokens cuyo claim `tipo` sea exactamente "acceso". Cualquier otro
    tipo (por ejemplo "compartir") se rechaza para que no sirva como credencial.
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


def crear_token_compartir(simulacion_id: int) -> str:
    """Genera un token firmado para compartir una simulacion con el cliente.

    El token incorpora el identificador de la simulacion y un tipo distinto al
    de autenticacion, de modo que no pueda usarse como token de acceso. Expira
    segun la configuracion (`dias_expiracion_token_compartir`).
    """

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(days=configuracion.dias_expiracion_token_compartir)
    contenido = {
        "sub": str(simulacion_id),
        "tipo": "compartir",
        "iat": ahora,
        "exp": expiracion,
    }
    return jwt.encode(
        contenido, configuracion.clave_secreta, algorithm=configuracion.algoritmo_jwt
    )


def leer_token_compartir(token: str) -> tuple[int | None, bool]:
    """Valida un token de compartir.

    Devuelve la tupla (simulacion_id, expirado). Si el token es invalido por
    otra razon devuelve (None, False); si caduco devuelve (None, True).
    """

    try:
        contenido = jwt.decode(
            token,
            configuracion.clave_secreta,
            algorithms=[configuracion.algoritmo_jwt],
        )
    except ExpiredSignatureError:
        return None, True
    except InvalidTokenError:
        return None, False

    if contenido.get("tipo") != "compartir":
        return None, False
    try:
        return int(contenido["sub"]), False
    except (KeyError, ValueError, TypeError):
        return None, False
