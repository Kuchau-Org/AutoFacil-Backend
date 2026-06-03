"""Modelo ORM de una simulacion de credito vehicular."""

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modelos.base import MarcasTiempoMixin, TipoMonto, TipoTasaColumna
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    TipoGracia,
    TipoTasa,
)


class Simulacion(Base, MarcasTiempoMixin):
    """Resultado completo de una simulacion, junto con sus parametros de entrada."""

    __tablename__ = "simulaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    # Etiqueta opcional para reconocer la simulacion.
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)

    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    vehiculo_id: Mapped[int] = mapped_column(ForeignKey("vehiculos.id"), nullable=False)
    # Asesor propietario de la simulacion (aislamiento de datos por usuario).
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)

    estado: Mapped[EstadoSimulacion] = mapped_column(
        SqlEnum(EstadoSimulacion), nullable=False, default=EstadoSimulacion.CALCULADA
    )
    moneda: Mapped[Moneda] = mapped_column(SqlEnum(Moneda), nullable=False)
    tipo_cambio_referencial: Mapped[float | None] = mapped_column(
        TipoTasaColumna, nullable=True
    )

    # Parametros de entrada de la operacion.
    precio_vehiculo: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    cuota_inicial: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    porcentaje_cuota_inicial: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)
    monto_financiado: Mapped[float] = mapped_column(TipoMonto, nullable=False)
    plazo_meses: Mapped[int] = mapped_column(Integer, nullable=False)

    tipo_tasa: Mapped[TipoTasa] = mapped_column(SqlEnum(TipoTasa), nullable=False)
    tasa_ingresada: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)
    capitalizacion: Mapped[Capitalizacion | None] = mapped_column(
        SqlEnum(Capitalizacion), nullable=True
    )
    tea_equivalente: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)
    tem: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False)

    tipo_gracia: Mapped[TipoGracia] = mapped_column(SqlEnum(TipoGracia), nullable=False)
    meses_gracia: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    # Cuota balon (Compra Inteligente): porcentaje del precio y su importe.
    porcentaje_cuota_final: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    cuota_final: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    # Seguros y cargos aplicados al credito.
    seguro_desgravamen_anual: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    # El desgravamen solo se cobra con consentimiento expreso (Res. SBS 890-2025).
    desgravamen_consentido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    seguro_vehicular_mensual: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    # GPS: instalacion (cargo unico), mantenimiento (mensual) y reposicion
    # (tarifario referencial, no se cobra al contratar).
    gps_instalacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gps_mantenimiento_mensual: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    gps_reposicion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    # Gastos de terceros que se financian (se suman al monto financiado).
    gastos_notariales: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    gastos_registrales: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    tasacion: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    # Total de gastos de terceros financiados (incluidos en el monto financiado).
    gastos_iniciales: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cok_anual: Mapped[float] = mapped_column(TipoTasaColumna, nullable=False, default=0)
    # Tasa de descuento usada para el VAN (por defecto igual al COK).
    tasa_descuento_van: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    # Tasa moratoria nominal anual (no capitalizable), informativa para la hoja
    # resumen del cliente; no entra en el calculo de la TCEA.
    tasa_moratoria_anual: Mapped[float] = mapped_column(
        TipoTasaColumna, nullable=False, default=0
    )
    # Datos de la poliza para la hoja resumen (art. 25 Reglamento SBS).
    aseguradora: Mapped[str | None] = mapped_column(String(120), nullable=True)
    numero_poliza: Mapped[str | None] = mapped_column(String(80), nullable=True)
    coberturas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resultados calculados.
    cuota_mensual: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    cuota_total_promedio: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    van: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    tir_mensual: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)
    tir_anual: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)
    tcea: Mapped[float | None] = mapped_column(TipoTasaColumna, nullable=True)
    costo_total_credito: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_intereses: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_amortizado: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    total_seguros: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)
    # Cargo unico cobrado al desembolso (instalacion de GPS; afecta la TCEA).
    total_cargos_desembolso: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    # Mantenimiento de GPS cobrado dentro de las cuotas (afecta la TCEA).
    total_gps_mantenimiento: Mapped[float] = mapped_column(
        TipoMonto, nullable=False, default=0
    )
    monto_total_pagado: Mapped[float] = mapped_column(TipoMonto, nullable=False, default=0)

    # Relaciones de navegacion.
    cliente = relationship("Cliente")
    vehiculo = relationship("Vehiculo")
    usuario = relationship("Usuario")
    cronograma = relationship(
        "CronogramaPago",
        back_populates="simulacion",
        cascade="all, delete-orphan",
        order_by="CronogramaPago.numero_periodo",
    )
