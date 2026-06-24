"""Rutas de autenticacion: login, registro y perfil del usuario."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.auth import (
    CredencialesLogin,
    RegistroRequest,
    TokenRespuesta,
)
from app.esquemas.usuario import UsuarioRespuesta
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual
from app.seguridad.hash import hashear_password, verificar_password
from app.seguridad.jwt import crear_token_acceso
from app.utilidades.respuestas import error_autenticacion, error_conflicto

enrutador = APIRouter(prefix="/auth", tags=["Autenticacion"])


def _autenticar(sesion: Session, identificador: str, password: str) -> Usuario:
    """Valida las credenciales y devuelve el usuario autenticado.

    El identificador puede ser el nombre de usuario o el correo. Se resuelve sin
    ambiguedad: si contiene '@' se interpreta como correo (en minusculas), de lo
    contrario como nombre de usuario. Los nombres de usuario no pueden contener
    '@' (ver `validar_usuario`), por lo que jamas colisionan con un correo.
    """

    identificador = (identificador or "").strip()
    if "@" in identificador:
        usuario = (
            sesion.query(Usuario)
            .filter(Usuario.correo == identificador.lower())
            .first()
        )
    else:
        usuario = (
            sesion.query(Usuario).filter(Usuario.usuario == identificador).first()
        )
    if usuario is None or not verificar_password(password, usuario.password_hash):
        raise error_autenticacion("Usuario o contrasena incorrectos.")
    if not usuario.activo:
        raise error_autenticacion("El usuario se encuentra inactivo.")
    return usuario


@enrutador.post(
    "/login",
    response_model=TokenRespuesta,
    summary="Iniciar sesion (formulario OAuth2)",
)
def login(
    datos: OAuth2PasswordRequestForm = Depends(),
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:
    """Inicia sesion por formulario OAuth2 (usuario o correo en `username`)."""

    usuario = _autenticar(sesion, datos.username, datos.password)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.post(
    "/login-json",
    response_model=TokenRespuesta,
    summary="Iniciar sesion (cuerpo JSON)",
)
def login_json(
    credenciales: CredencialesLogin,
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:
    """Inicia sesion por cuerpo JSON."""

    usuario = _autenticar(sesion, credenciales.usuario, credenciales.password)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.post(
    "/registro",
    response_model=TokenRespuesta,
    summary="Registrar un nuevo usuario e iniciar sesion",
)
def registro(
    datos: RegistroRequest,
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:
    """Registra un nuevo usuario operador del sistema y devuelve su token.

    El registro es publico para que el personal de la entidad financiera pueda
    crear su propia cuenta. Tras crear la cuenta se devuelve el token JWT para
    iniciar sesion de inmediato.
    """

    duplicado = (
        sesion.query(Usuario)
        .filter(or_(Usuario.usuario == datos.usuario, Usuario.correo == datos.correo))
        .first()
    )
    if duplicado is not None:
        raise error_conflicto("El usuario o el correo ya estan registrados.")

    usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        correo=datos.correo,
        usuario=datos.usuario,
        password_hash=hashear_password(datos.password),
        activo=True,
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.get("/me", response_model=UsuarioRespuesta, summary="Perfil del usuario autenticado")
def perfil_actual(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    """Devuelve los datos del usuario autenticado."""

    return usuario_actual
