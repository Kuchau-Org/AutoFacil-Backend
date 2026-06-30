"""Modelo ORM del vehiculo que el usuario evalua financiar."""

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.modelos.base import MarcasTiempoMixin, TipoMonto
from app.modelos.enumeraciones import Moneda


class Vehiculo(Base, MarcasTiempoMixin):
    """Vehiculo que el usuario registra para simular su financiamiento."""

    __tablename__ = "vehiculos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Usuario duenio del vehiculo.
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False, index=True
    )
    marca: Mapped[str] = mapped_column(String(80), nullable=False)
    modelo: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    precio: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    moneda: Mapped[Moneda] = mapped_column(
        SqlEnum(Moneda), nullable=False, default=Moneda.SOLES
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # URL de una imagen del vehiculo (opcional). Si no se indica, el frontend
    # genera una imagen referencial a partir de la marca.
    url_imagen: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Baja logica interna: oculta el vehiculo sin borrar el historial.
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
