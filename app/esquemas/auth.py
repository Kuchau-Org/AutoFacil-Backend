"""Esquemas Pydantic para autenticacion y registro de usuarios."""

from pydantic import BaseModel, Field, field_validator

from app.esquemas.comunes import (
    validar_correo_obligatorio,
    validar_password_bcrypt,
    validar_usuario,
)


class TokenRespuesta(BaseModel):
    """Respuesta entregada tras un inicio de sesion exitoso."""

    access_token: str
    token_type: str = "bearer"


class CredencialesLogin(BaseModel):
    """Credenciales aceptadas por el inicio de sesion en formato JSON."""

    usuario: str = Field(..., description="Nombre de usuario o correo")
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"usuario": "admin", "password": "Admin123"}]
        }
    }


class RegistroRequest(BaseModel):
    """Datos para el registro publico de un nuevo usuario del sistema."""

    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    correo: str = Field(..., max_length=180)
    usuario: str = Field(..., min_length=3, max_length=60)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str) -> str:
        return validar_correo_obligatorio(valor)

    @field_validator("usuario")
    @classmethod
    def _validar_usuario(cls, valor: str) -> str:
        return validar_usuario(valor)

    @field_validator("password")
    @classmethod
    def _validar_password(cls, valor: str) -> str:
        return validar_password_bcrypt(valor)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str) -> str:
        if valor.strip() == "":
            raise ValueError("El campo no puede estar vacio.")
        return valor.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Lucia",
                    "apellido": "Garcia",
                    "correo": "lucia.garcia@autofacil.local",
                    "usuario": "lgarcia",
                    "password": "Clave123",
                }
            ]
        }
    }
