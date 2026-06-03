"""Esquemas Pydantic para la entidad Cliente."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.esquemas.comunes import DecimalNumero, texto_obligatorio, validar_correo
from app.modelos.enumeraciones import Moneda


class ClienteBase(BaseModel):
    """Campos editables de un cliente evaluado para credito."""

    tipo_documento: str = Field(default="DNI", max_length=20)
    numero_documento: str = Field(..., min_length=1, max_length=30)
    nombres: str = Field(..., min_length=1, max_length=120)
    apellidos: str = Field(..., min_length=1, max_length=120)
    correo: str | None = Field(default=None, max_length=180)
    telefono: str | None = Field(default=None, max_length=30)
    direccion: str | None = Field(default=None, max_length=255)
    fecha_nacimiento: date | None = None
    ingreso_mensual: DecimalNumero = Field(default=Decimal("0"), ge=0)
    gastos_mensuales: DecimalNumero = Field(default=Decimal("0"), ge=0)
    otras_deudas: DecimalNumero = Field(default=Decimal("0"), ge=0)
    moneda_ingresos: Moneda = Moneda.SOLES

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str | None) -> str | None:
        return validar_correo(valor)

    @field_validator("numero_documento", "nombres", "apellidos")
    @classmethod
    def _validar_obligatorios(cls, valor: str, info) -> str:
        return texto_obligatorio(valor, info.field_name)


class ClienteCrear(ClienteBase):
    """Datos para crear un cliente."""


class ClienteActualizar(BaseModel):
    """Campos opcionales para actualizar parcialmente un cliente."""

    tipo_documento: str | None = Field(default=None, max_length=20)
    numero_documento: str | None = Field(default=None, max_length=30)
    nombres: str | None = Field(default=None, max_length=120)
    apellidos: str | None = Field(default=None, max_length=120)
    correo: str | None = Field(default=None, max_length=180)
    telefono: str | None = Field(default=None, max_length=30)
    direccion: str | None = Field(default=None, max_length=255)
    fecha_nacimiento: date | None = None
    ingreso_mensual: Decimal | None = Field(default=None, ge=0)
    gastos_mensuales: Decimal | None = Field(default=None, ge=0)
    otras_deudas: Decimal | None = Field(default=None, ge=0)
    moneda_ingresos: Moneda | None = None
    # `activo` no se edita desde aqui: dar de baja a un cliente se hace solo con
    # el endpoint DELETE, para que la edicion normal no pueda reactivarlo o
    # desactivarlo sin querer.

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str | None) -> str | None:
        return validar_correo(valor)

    @field_validator("numero_documento", "nombres", "apellidos")
    @classmethod
    def _validar_obligatorios(cls, valor: str | None, info) -> str | None:
        # En una actualizacion parcial el campo puede omitirse (None), pero si
        # se envia no puede quedar vacio.
        if valor is None:
            return None
        return texto_obligatorio(valor, info.field_name)


class ClienteRespuesta(ClienteBase):
    """Representacion completa de un cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime
