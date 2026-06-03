"""Modelo ORM de cada fila del cronograma de pagos de una simulacion."""

from datetime import date

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modelos.base import TipoMonto
from app.modelos.enumeraciones import TipoPeriodo


class CronogramaPago(Base):
    """Detalle de un periodo del cronograma: saldo, interes, amortizacion y cargos."""

    __tablename__ = "cronogramas_pago"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    simulacion_id: Mapped[int] = mapped_column(
        ForeignKey("simulaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero_periodo: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_periodo: Mapped[TipoPeriodo] = mapped_column(SqlEnum(TipoPeriodo), nullable=False)

    saldo_inicial: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    interes: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    amortizacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    seguro_desgravamen: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    seguro_vehicular: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gps_mantenimiento: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cuota_ordinaria: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cuota_final_extraordinaria: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    cuota_total: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    saldo_final: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    simulacion = relationship("Simulacion", back_populates="cronograma")
