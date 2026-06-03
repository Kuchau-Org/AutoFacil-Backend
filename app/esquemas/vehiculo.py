"""Esquemas Pydantic para la entidad Vehiculo."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.esquemas.comunes import DecimalNumero, texto_obligatorio
from app.modelos.enumeraciones import Moneda


class VehiculoBase(BaseModel):
    """Campos editables de una oferta vehicular."""

    marca: str = Field(..., min_length=1, max_length=80)
    modelo: str = Field(..., min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    anio: int = Field(..., ge=1900, le=2100)
    tipo: str | None = Field(default=None, max_length=60)
    precio: DecimalNumero = Field(..., gt=0)
    moneda: Moneda = Moneda.SOLES
    descripcion: str | None = None
    url_imagen: str | None = Field(default=None, max_length=500)

    @field_validator("marca", "modelo")
    @classmethod
    def _validar_obligatorios(cls, valor: str, info) -> str:
        return texto_obligatorio(valor, info.field_name)


class VehiculoCrear(VehiculoBase):
    """Datos para crear un vehiculo."""


class VehiculoActualizar(BaseModel):
    """Campos opcionales para actualizar parcialmente un vehiculo."""

    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    tipo: str | None = Field(default=None, max_length=60)
    precio: Decimal | None = Field(default=None, gt=0)
    moneda: Moneda | None = None
    descripcion: str | None = None
    url_imagen: str | None = Field(default=None, max_length=500)
    # `activo` no se edita por aqui: la baja logica es exclusiva del endpoint
    # DELETE, para que la edicion no la pueda esquivar.

    @field_validator("marca", "modelo")
    @classmethod
    def _validar_obligatorios(cls, valor: str | None, info) -> str | None:
        if valor is None:
            return None
        return texto_obligatorio(valor, info.field_name)


class VehiculoRespuesta(VehiculoBase):
    """Representacion completa de un vehiculo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime
