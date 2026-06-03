"""Esquemas Pydantic para la entidad Usuario."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.esquemas.comunes import (
    validar_correo,
    validar_password_bcrypt,
    validar_usuario,
)


class UsuarioBase(BaseModel):
    """Campos comunes de creacion y actualizacion de usuarios."""

    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    correo: str = Field(..., max_length=180)
    usuario: str = Field(..., min_length=3, max_length=60)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str) -> str:
        return validar_correo(valor)


class UsuarioCrear(UsuarioBase):
    """Datos para crear un usuario, incluida la contrasena en texto plano."""

    password: str = Field(..., min_length=6, max_length=128)


class UsuarioRespuesta(UsuarioBase):
    """Representacion publica de un usuario, sin la contrasena."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class PerfilActualizar(BaseModel):
    """Datos para que el usuario actualice su propio perfil."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido: str | None = Field(default=None, min_length=1, max_length=120)
    correo: str | None = Field(default=None, max_length=180)
    usuario: str | None = Field(default=None, min_length=3, max_length=60)
    password_actual: str | None = Field(default=None, max_length=128)
    password_nueva: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str | None) -> str | None:
        return validar_correo(valor)

    @field_validator("usuario")
    @classmethod
    def _validar_usuario(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return validar_usuario(valor)

    @field_validator("password_nueva")
    @classmethod
    def _validar_password(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return validar_password_bcrypt(valor)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if valor.strip() == "":
            raise ValueError("El campo no puede estar vacio.")
        return valor.strip()
