"""Validadores y tipos reutilizables compartidos por varios esquemas Pydantic."""

import re
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Tipo de importe/tasa que se valida como Decimal en la entrada (preservando la
# precision) pero se serializa como numero (float) en las respuestas JSON, para
# que el frontend reciba numeros y no cadenas de texto.
DecimalNumero = Annotated[
    Decimal,
    PlainSerializer(
        lambda valor: float(valor) if valor is not None else None,
        return_type=float,
        when_used="json",
    ),
]

# Patron de correo deliberadamente permisivo: admite dominios de uso local como
# `.local`, requeridos por los datos semilla del proyecto, sin las
# restricciones de dominios reservados que aplica `email-validator`.
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_correo(valor: str | None) -> str | None:
    """Valida un correo opcional (permite dominios locales); vacio -> None."""

    if valor is None:
        return None
    valor = valor.strip().lower()
    if valor == "":
        return None
    if not _PATRON_CORREO.match(valor):
        raise ValueError("El correo electronico no tiene un formato valido.")
    return valor


def validar_correo_obligatorio(valor: str | None) -> str:
    """Valida un correo OBLIGATORIO (login y registro de usuarios).

    Normaliza (recorta y minusculas) y rechaza el valor vacio en lugar de
    convertirlo silenciosamente a NULL. Lanza `ValueError` en espanol si falta
    o tiene formato invalido.
    """

    if valor is None or valor.strip() == "":
        raise ValueError("El correo electronico es obligatorio.")
    valor = valor.strip().lower()
    if not _PATRON_CORREO.match(valor):
        raise ValueError("El correo electronico no tiene un formato valido.")
    return valor


def validar_usuario(valor: str) -> str:
    """Normaliza y valida un nombre de usuario de inicio de sesion.

    Recorta espacios y rechaza valores vacios o puramente numericos (estos
    ultimos generan ambiguedad con identificadores internos). El nombre de
    usuario se conserva tal cual, sin pasar a minusculas, salvo el recorte.
    """

    if valor is None:
        raise ValueError("El nombre de usuario es obligatorio.")
    valor = valor.strip()
    if valor == "":
        raise ValueError("El nombre de usuario es obligatorio.")
    if valor.isdigit():
        raise ValueError("El nombre de usuario no puede ser solo numeros.")
    if "@" in valor:
        raise ValueError("El nombre de usuario no puede contener '@'.")
    return valor


def validar_password_bcrypt(valor: str) -> str:
    """Valida que la contrasena no exceda el limite de 72 bytes de bcrypt.

    bcrypt ignora silenciosamente los bytes posteriores al numero 72; para
    evitar comportamientos sorpresivos se rechaza explicitamente con un mensaje
    claro. El conteo se hace sobre la codificacion UTF-8 (no sobre caracteres).
    """

    if valor is None or valor == "":
        raise ValueError("La contrasena es obligatoria.")
    if len(valor.encode("utf-8")) > 72:
        raise ValueError(
            "La contrasena es demasiado larga (maximo 72 bytes en UTF-8)."
        )
    return valor


def texto_obligatorio(valor: str, campo: str) -> str:
    """Recorta un texto y rechaza el valor vacio para un campo obligatorio."""

    if valor is None or valor.strip() == "":
        raise ValueError(f"El campo {campo} no puede estar vacio.")
    return valor.strip()
