"""Modelo ORM del cliente al que el asesor ofrece el credito.

Cada asesor gestiona su propia cartera de clientes: el cliente pertenece al
usuario que lo registro (`usuario_id`) y no es visible para otros asesores.
"""

from datetime import date

from sqlalchemy import Boolean, Date, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.modelos.base import MarcasTiempoMixin, TipoMonto
from app.modelos.enumeraciones import Moneda


class Cliente(Base, MarcasTiempoMixin):
    """Datos del cliente evaluado para un credito vehicular."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Asesor propietario del cliente (aislamiento de datos por usuario).
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False, index=True
    )
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False, default="DNI")
    # El documento es unico por asesor (no globalmente), se valida en la ruta.
    numero_documento: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    nombres: Mapped[str] = mapped_column(String(120), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str | None] = mapped_column(String(180), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    ingreso_mensual: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gastos_mensuales: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    otras_deudas: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    moneda_ingresos: Mapped[Moneda] = mapped_column(
        SqlEnum(Moneda), nullable=False, default=Moneda.SOLES
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
