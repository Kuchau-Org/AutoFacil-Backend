"""Modelo ORM de una simulacion de credito vehicular "Compra Inteligente"."""

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modelos.base import MarcasTiempoMixin, TipoMonto, TipoTasaColumna
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    Plan,
    TipoTasa,
)


class Simulacion(Base, MarcasTiempoMixin):
    """Resultado completo de una simulacion, junto con sus parametros de entrada."""

    __tablename__ = "simulaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    # Etiqueta opcional para reconocer la simulacion.
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)

    vehiculo_id: Mapped[int] = mapped_column(ForeignKey("vehiculos.id"), nullable=False)
    # Usuario duenio de la simulacion (cada quien ve solo las suyas).
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)

    estado: Mapped[EstadoSimulacion] = mapped_column(
        SqlEnum(EstadoSimulacion), nullable=False, default=EstadoSimulacion.CALCULADA
    )
    moneda: Mapped[Moneda] = mapped_column(SqlEnum(Moneda), nullable=False)
    tipo_cambio_referencial: Mapped[float | None] = mapped_column(
        TipoTasaColumna, nullable=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    # --- Parametros de entrada ---
    precio_vehiculo: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    plan: Mapped[Plan] = mapped_column(SqlEnum(Plan), nullable=False)
    porcentaje_cuota_inicial: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)

    tipo_tasa: Mapped[TipoTasa] = mapped_column(SqlEnum(TipoTasa), nullable=False)
    tasa_ingresada: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)
    capitalizacion: Mapped[Capitalizacion | None] = mapped_column(
        SqlEnum(Capitalizacion), nullable=True
    )

    meses_gracia_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meses_gracia_parcial: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Costos / gastos iniciales (monto + si se financia o se paga al contado).
    costo_notarial: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    costo_notarial_financiado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    costo_registral: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    costo_registral_financiado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    costo_tasacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    costo_tasacion_financiado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comision_estudio: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    comision_estudio_financiado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comision_activacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    comision_activacion_financiado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Costos / gastos periodicos (por cuota).
    gps_periodico: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    portes_periodico: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gastos_adm_periodico: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    # Seguros: desgravamen mensual y riesgo (todo riesgo) anual, ambos en decimal.
    seguro_desgravamen_mensual: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    seguro_riesgo_anual: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)

    cok_anual: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)

    # --- Resultados derivados ---
    numero_cuotas: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_anios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    porcentaje_cuota_final: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    cuota_inicial: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cuota_final: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    monto_prestamo: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    saldo_financiado: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    tea_equivalente: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)
    tem: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)
    seguro_riesgo_periodico: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_costos_financiados: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_costos_efectivo: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    cuota_mensual: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cok_mensual: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)
    van: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    tir_mensual: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)
    tir_anual: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)
    tcea: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)

    total_intereses: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_amortizado: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_seguro_desgravamen: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_seguro_riesgo: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_gps: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_portes: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_gastos_adm: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    monto_total_pagado: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    # Relaciones de navegacion.
    vehiculo = relationship("Vehiculo")
    usuario = relationship("Usuario")
    cronograma = relationship(
        "CronogramaPago",
        back_populates="simulacion",
        cascade="all, delete-orphan",
        order_by="CronogramaPago.numero_periodo",
    )
