"""Modelo ORM para el registro de auditoria de operaciones del sistema."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.modelos.base import _ahora_utc


class AuditoriaOperacion(Base):
    """Traza basica de creacion, edicion y calculo de entidades sensibles."""

    __tablename__ = "auditoria_operaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    entidad: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=_ahora_utc, nullable=False
    )
