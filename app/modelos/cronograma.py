"""Modelo ORM de cada fila del cronograma de pagos de una simulacion."""

from datetime import date

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modelos.base import TipoMonto
from app.modelos.enumeraciones import TipoPeriodo


class CronogramaPago(Base):
    """Detalle de un periodo: tramo del cuoton, tramo regular y flujo del deudor."""

    __tablename__ = "cronogramas_pago"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    simulacion_id: Mapped[int] = mapped_column(
        ForeignKey("simulaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero_periodo: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_periodo: Mapped[TipoPeriodo] = mapped_column(SqlEnum(TipoPeriodo), nullable=False)

    # Tramo del cuoton (cuota final diferida).
    saldo_inicial_cuoton: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    interes_cuoton: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    amortizacion_cuoton: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    desgravamen_cuoton: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    saldo_final_cuoton: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    # Tramo de la cuota regular.
    saldo_inicial: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    interes: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cuota: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    amortizacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    seguro_desgravamen: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    seguro_riesgo: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gps: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    portes: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gastos_adm: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    saldo_final: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    flujo: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    simulacion = relationship("Simulacion", back_populates="cronograma")
