"""Funciones de hash de contrasenas basadas en bcrypt.

Se usa la libreria `bcrypt` de forma directa para generar y verificar hashes.
bcrypt opera sobre bytes y limita la entrada a 72 bytes, por lo que la
contrasena se codifica en UTF-8 antes de procesarla.
"""

import bcrypt


def hashear_password(password: str) -> str:
    """Genera el hash bcrypt de una contrasena en texto plano.

    bcrypt limita la entrada a 72 bytes; se valida explicitamente para no
    truncar de forma silenciosa una contrasena mas larga.
    """

    bytes_password = password.encode("utf-8")
    if len(bytes_password) > 72:
        raise ValueError(
            "La contrasena es demasiado larga (maximo 72 bytes en UTF-8)."
        )
    sal = bcrypt.gensalt()
    return bcrypt.hashpw(bytes_password, sal).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Verifica que una contrasena coincida con su hash almacenado."""

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        # Un hash malformado se considera no coincidente en lugar de propagar el error.
        return False
