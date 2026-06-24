"""Rutas para que el usuario consulte y actualice su propio perfil."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.usuario import PerfilActualizar, UsuarioRespuesta
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual
from app.seguridad.hash import hashear_password, verificar_password
from app.utilidades.respuestas import error_conflicto, error_validacion

enrutador = APIRouter(prefix="/perfil", tags=["Perfil"])


@enrutador.get("", response_model=UsuarioRespuesta, summary="Ver mi perfil")
def ver_perfil(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    """Devuelve los datos del perfil del usuario autenticado."""

    return usuario_actual


@enrutador.put("", response_model=UsuarioRespuesta, summary="Actualizar mi perfil")
def actualizar_perfil(
    datos: PerfilActualizar,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Usuario:
    """Actualiza nombre, apellido, correo o contrasena (requiere la contrasena actual)."""

    if datos.correo and datos.correo != usuario_actual.correo:
        existe = (
            sesion.query(Usuario)
            .filter(Usuario.correo == datos.correo, Usuario.id != usuario_actual.id)
            .first()
        )
        if existe is not None:
            raise error_conflicto("El correo ya esta registrado por otro usuario.")
        usuario_actual.correo = datos.correo

    if datos.usuario and datos.usuario != usuario_actual.usuario:
        existe = (
            sesion.query(Usuario)
            .filter(Usuario.usuario == datos.usuario, Usuario.id != usuario_actual.id)
            .first()
        )
        if existe is not None:
            raise error_conflicto("El nombre de usuario ya esta en uso.")
        usuario_actual.usuario = datos.usuario

    if datos.nombre:
        usuario_actual.nombre = datos.nombre
    if datos.apellido:
        usuario_actual.apellido = datos.apellido

    if datos.password_nueva:
        if not datos.password_actual or not verificar_password(
            datos.password_actual, usuario_actual.password_hash
        ):
            raise error_validacion("La contrasena actual es incorrecta.")
        usuario_actual.password_hash = hashear_password(datos.password_nueva)

    sesion.commit()
    sesion.refresh(usuario_actual)
    return usuario_actual
