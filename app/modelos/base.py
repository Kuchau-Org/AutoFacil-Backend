"""Mixins y tipos de columna reutilizados por los modelos ORM."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

# Tipos de columna estandarizados para importes monetarios y tasas. Los valores
# persistidos son resultados finales ya redondeados para presentacion; la alta
# precision se conserva en memoria durante el calculo con `Decimal`.
TipoMonto = Numeric(18, 2)
TipoTasaColumna = Numeric(18, 10)


def _ahora_utc() -> datetime:
    """Devuelve la marca temporal actual en UTC sin informacion de zona."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class MarcasTiempoMixin:
    """Agrega columnas de auditoria temporal a un modelo."""

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=_ahora_utc, nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )
