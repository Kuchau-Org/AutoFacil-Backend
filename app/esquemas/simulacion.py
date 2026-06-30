"""Esquemas Pydantic de simulaciones (tasas y porcentajes en formato decimal)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    Plan,
    TipoTasa,
)


class ParametrosFinancieros(BaseModel):
    """Parametros financieros que condicionan el calculo de una simulacion."""

    moneda: Moneda = Moneda.SOLES
    tipo_cambio_referencial: Decimal | None = Field(default=None, ge=0)
    # El plan determina el numero de cuotas (N) y la cuota final (pCF).
    plan: Plan = Plan.PLAN_36
    porcentaje_cuota_inicial: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    tipo_tasa: TipoTasa = TipoTasa.NOMINAL
    valor_tasa: Decimal = Field(..., ge=0, description="Tasa en formato decimal (0.15 = 15%)")
    # Obligatoria solo cuando la tasa es nominal (TNA): diaria o mensual.
    capitalizacion: Capitalizacion | None = None
    # Gracia al inicio: meses de gracia total y, a continuacion, de gracia parcial.
    meses_gracia_total: int = Field(default=0, ge=0)
    meses_gracia_parcial: int = Field(default=0, ge=0)
    # Costos / gastos iniciales: monto y si se financia (entra al prestamo) o se
    # paga al contado (efectivo).
    costo_notarial: Decimal = Field(default=Decimal("0"), ge=0)
    costo_notarial_financiado: bool = True
    costo_registral: Decimal = Field(default=Decimal("0"), ge=0)
    costo_registral_financiado: bool = True
    costo_tasacion: Decimal = Field(default=Decimal("0"), ge=0)
    costo_tasacion_financiado: bool = True
    comision_estudio: Decimal = Field(default=Decimal("0"), ge=0)
    comision_estudio_financiado: bool = True
    comision_activacion: Decimal = Field(default=Decimal("0"), ge=0)
    comision_activacion_financiado: bool = True
    # Costos / gastos periodicos (por cuota).
    gps_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    portes_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    gastos_adm_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    # Seguros: desgravamen como % mensual; riesgo (todo riesgo) como % anual del precio.
    seguro_desgravamen_mensual: Decimal = Field(default=Decimal("0"), ge=0)
    seguro_riesgo_anual: Decimal = Field(default=Decimal("0"), ge=0)
    # Costo de oportunidad del dinero del usuario (TEA) para el VAN.
    cok_anual: Decimal = Field(default=Decimal("0"), ge=0)
    fecha_inicio: date | None = None

    @model_validator(mode="after")
    def validar_reglas(self) -> "ParametrosFinancieros":
        """Valida la coherencia de la tasa nominal y de los periodos de gracia."""

        if self.tipo_tasa == TipoTasa.NOMINAL and self.capitalizacion is None:
            raise ValueError("La capitalizacion es obligatoria cuando la tasa es nominal.")
        if self.meses_gracia_total + self.meses_gracia_parcial >= self.plan.numero_cuotas:
            raise ValueError("Los meses de gracia deben ser menores que el numero de cuotas.")
        return self


class SimulacionCalcularRequest(ParametrosFinancieros):
    """Solicitud para calcular una simulacion (con o sin persistencia)."""

    vehiculo_id: int
    nombre: str | None = Field(default=None, max_length=150)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "vehiculo_id": 1,
                    "nombre": "Compra Inteligente - Plan 36",
                    "moneda": "PEN",
                    "plan": "PLAN_36",
                    "porcentaje_cuota_inicial": 0.20,
                    "tipo_tasa": "NOMINAL",
                    "valor_tasa": 0.15,
                    "capitalizacion": "DIARIA",
                    "meses_gracia_total": 3,
                    "meses_gracia_parcial": 3,
                    "costo_notarial": 100,
                    "costo_notarial_financiado": True,
                    "costo_registral": 75,
                    "costo_registral_financiado": True,
                    "gps_periodico": 20,
                    "portes_periodico": 3.5,
                    "gastos_adm_periodico": 3.5,
                    "seguro_desgravamen_mensual": 0.00049,
                    "seguro_riesgo_anual": 0.003,
                    "cok_anual": 0.50,
                    "fecha_inicio": "2026-01-01",
                }
            ]
        }
    }


class SimulacionGuardarRequest(SimulacionCalcularRequest):
    """Solicitud para crear y guardar (o editar) una simulacion calculada."""

    estado: EstadoSimulacion = EstadoSimulacion.CALCULADA
    # Al editar, conserva el precio original de la propuesta salvo que se pida
    # explicitamente actualizarlo al precio actual del vehiculo.
    actualizar_precio: bool = False


class IndicadoresSimulacion(BaseModel):
    """Conjunto de montos derivados e indicadores calculados de una simulacion."""

    moneda: Moneda
    precio_vehiculo: float
    plan: Plan
    numero_cuotas: int
    numero_anios: int
    porcentaje_cuota_inicial: float
    cuota_inicial: float
    porcentaje_cuota_final: float
    cuota_final: float
    monto_prestamo: float
    saldo_financiado: float
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    tea_equivalente: float
    tem: float
    meses_gracia_total: int
    meses_gracia_parcial: int
    seguro_desgravamen_mensual: float
    seguro_riesgo_anual: float
    seguro_riesgo_periodico: float
    gps_periodico: float
    portes_periodico: float
    gastos_adm_periodico: float
    total_costos_financiados: float
    total_costos_efectivo: float
    cuota_mensual: float
    cok_anual: float
    cok_mensual: float
    van: float
    tir_mensual: float | None
    tir_anual: float | None
    tcea: float | None
    total_intereses: float
    total_amortizado: float
    total_seguro_desgravamen: float
    total_seguro_riesgo: float
    total_gps: float
    total_portes: float
    total_gastos_adm: float
    monto_total_pagado: float


class ResultadoCalculo(IndicadoresSimulacion):
    """Resultado del calculo de previsualizacion: indicadores y cronograma."""

    cronograma: list[CronogramaFilaRespuesta]


class SimulacionRespuesta(BaseModel):
    """Representacion completa de una simulacion persistida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str | None
    vehiculo_id: int
    usuario_id: int
    estado: EstadoSimulacion
    moneda: Moneda
    tipo_cambio_referencial: float | None
    fecha_inicio: date
    # Parametros de entrada.
    precio_vehiculo: float
    plan: Plan
    porcentaje_cuota_inicial: float
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    meses_gracia_total: int
    meses_gracia_parcial: int
    costo_notarial: float
    costo_notarial_financiado: bool
    costo_registral: float
    costo_registral_financiado: bool
    costo_tasacion: float
    costo_tasacion_financiado: bool
    comision_estudio: float
    comision_estudio_financiado: bool
    comision_activacion: float
    comision_activacion_financiado: bool
    gps_periodico: float
    portes_periodico: float
    gastos_adm_periodico: float
    seguro_desgravamen_mensual: float
    seguro_riesgo_anual: float
    cok_anual: float
    # Resultados derivados.
    numero_cuotas: int
    numero_anios: int
    porcentaje_cuota_final: float
    cuota_inicial: float
    cuota_final: float
    monto_prestamo: float
    saldo_financiado: float
    tea_equivalente: float
    tem: float
    seguro_riesgo_periodico: float
    total_costos_financiados: float
    total_costos_efectivo: float
    cuota_mensual: float
    cok_mensual: float
    van: float
    tir_mensual: float | None
    tir_anual: float | None
    tcea: float | None
    total_intereses: float
    total_amortizado: float
    total_seguro_desgravamen: float
    total_seguro_riesgo: float
    total_gps: float
    total_portes: float
    total_gastos_adm: float
    monto_total_pagado: float
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SimulacionDetalle(SimulacionRespuesta):
    """Simulacion con datos descriptivos y cronograma asociado."""

    vehiculo_descripcion: str | None = None
    usuario_nombre: str | None = None
    cronograma: list[CronogramaFilaRespuesta] = []


class SimulacionListado(BaseModel):
    """Resumen de una simulacion para vistas de listado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str | None = None
    estado: EstadoSimulacion
    moneda: Moneda
    plan: Plan
    vehiculo_id: int
    vehiculo_descripcion: str | None = None
    monto_prestamo: float
    numero_cuotas: int
    cuota_mensual: float
    tcea: float | None
    fecha_creacion: datetime
