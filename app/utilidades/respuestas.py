"""Funciones auxiliares para construir respuestas y errores homogeneos."""

from fastapi import HTTPException, status


def error_no_encontrado(detalle: str) -> HTTPException:
    """Construye una excepcion HTTP 404 con el detalle indicado."""

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detalle)


def error_validacion(detalle: str) -> HTTPException:
    """Construye una excepcion HTTP 400 para errores de validacion de negocio."""

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detalle)


def error_conflicto(detalle: str) -> HTTPException:
    """Construye una excepcion HTTP 409 para conflictos de unicidad."""

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalle)


def error_autenticacion(detalle: str) -> HTTPException:
    """Construye una excepcion HTTP 401 para fallos de autenticacion."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def error_permiso(detalle: str) -> HTTPException:
    """Construye una excepcion HTTP 403 para fallos de autorizacion."""

    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)
