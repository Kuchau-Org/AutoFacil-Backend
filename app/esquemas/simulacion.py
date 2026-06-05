"""Esquemas Pydantic para el calculo y la gestion de simulaciones.

Las tasas y porcentajes de entrada se expresan en formato decimal
(0.18 = 18%, 0.20 = 20% de cuota inicial). Los indicadores de salida tambien se
devuelven en formato decimal; el frontend los presenta como porcentaje.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    TipoGracia,
    TipoTasa,
)


class ParametrosFinancieros(BaseModel):
    """Parametros financieros que condicionan el calculo de una simulacion."""

    moneda: Moneda = Moneda.SOLES
    tipo_cambio_referencial: Decimal | None = Field(default=None, ge=0)
    tipo_tasa: TipoTasa = TipoTasa.EFECTIVA
    valor_tasa: Decimal = Field(..., ge=0, description="Tasa en formato decimal (0.18 = 18%)")
    capitalizacion: Capitalizacion | None = None
    plazo_meses: int = Field(..., gt=0)
    porcentaje_cuota_inicial: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    # Cuota balon (Compra Inteligente): porcentaje del precio que se paga al final.
    porcentaje_cuota_final: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    tipo_gracia: TipoGracia = TipoGracia.NINGUNA
    meses_gracia: int = Field(default=0, ge=0)
    # Seguro de desgravamen: solo se cobra con consentimiento expreso del cliente.
    seguro_desgravamen_anual: Decimal = Field(default=Decimal("0"), ge=0)
    desgravamen_consentido: bool = False
    # Seguro vehicular mensual (en la cuota).
    seguro_vehicular_mensual: Decimal = Field(default=Decimal("0"), ge=0)
    # GPS: instalacion (cargo unico), mantenimiento (mensual) y reposicion
    # (tarifario referencial, no se cobra al contratar).
    gps_instalacion: Decimal = Field(default=Decimal("0"), ge=0)
    gps_mantenimiento_mensual: Decimal = Field(default=Decimal("0"), ge=0)
    gps_reposicion: Decimal = Field(default=Decimal("0"), ge=0)
    # Gastos de terceros que se financian (se suman al monto financiado).
    gastos_notariales: Decimal = Field(default=Decimal("0"), ge=0)
    gastos_registrales: Decimal = Field(default=Decimal("0"), ge=0)
    tasacion: Decimal = Field(default=Decimal("0"), ge=0)
    cok_anual: Decimal = Field(default=Decimal("0"), ge=0)
    # Tasa de descuento del VAN (opcional). Si no se indica, se usa el COK.
    tasa_descuento_van: Decimal | None = Field(default=None, ge=0)
    # Tasa moratoria nominal anual (no capitalizable, segun la SBS): informativa
    # para la hoja resumen del cliente; no entra en el calculo de la TCEA.
    tasa_moratoria_anual: Decimal = Field(default=Decimal("0"), ge=0)
    # Datos de la poliza para la hoja resumen (art. 25 Reglamento SBS).
    aseguradora: str | None = Field(default=None, max_length=120)
    numero_poliza: str | None = Field(default=None, max_length=80)
    coberturas: str | None = Field(default=None, max_length=1000)
    fecha_inicio: date | None = None

    @model_validator(mode="after")
    def validar_reglas(self) -> "ParametrosFinancieros":
        """Valida la coherencia de la tasa nominal, la gracia y la cuota balon."""

        if self.tipo_tasa == TipoTasa.NOMINAL and self.capitalizacion is None:
            raise ValueError(
                "La capitalizacion es obligatoria cuando la tasa es nominal."
            )
        if self.tipo_gracia != TipoGracia.NINGUNA and self.meses_gracia >= self.plazo_meses:
            raise ValueError(
                "Los meses de gracia deben ser menores que el plazo total."
            )
        if self.porcentaje_cuota_inicial > 1:
            raise ValueError("La cuota inicial no puede superar el 100% del precio.")
        if self.porcentaje_cuota_inicial + self.porcentaje_cuota_final >= 1:
            raise ValueError(
                "La suma de la cuota inicial y la cuota balon no puede llegar al 100% del precio."
            )
        return self


class SimulacionCalcularRequest(ParametrosFinancieros):
    """Solicitud para calcular una simulacion (con o sin persistencia)."""

    cliente_id: int
    vehiculo_id: int
    nombre: str | None = Field(default=None, max_length=150)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "cliente_id": 1,
                    "vehiculo_id": 1,
                    "nombre": "Compra Inteligente a 48 meses",
                    "moneda": "PEN",
                    "tipo_tasa": "EFECTIVA",
                    "valor_tasa": 0.145,
                    "capitalizacion": None,
                    "plazo_meses": 48,
                    "porcentaje_cuota_inicial": 0.20,
                    "porcentaje_cuota_final": 0.40,
                    "tipo_gracia": "NINGUNA",
                    "meses_gracia": 0,
                    "seguro_desgravamen_anual": 0.006,
                    "desgravamen_consentido": True,
                    "seguro_vehicular_mensual": 85,
                    "gps_instalacion": 250,
                    "gps_mantenimiento_mensual": 0,
                    "gps_reposicion": 0,
                    "gastos_notariales": 180,
                    "gastos_registrales": 120,
                    "tasacion": 150,
                    "cok_anual": 0.12,
                    "tasa_descuento_van": 0.10,
                    "tasa_moratoria_anual": 0.18,
                    "aseguradora": "Seguros Ejemplo",
                    "numero_poliza": "POL-000123",
                    "coberturas": "Todo riesgo, robo y responsabilidad civil",
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
    """Conjunto de indicadores financieros calculados para una simulacion."""

    moneda: Moneda
    precio_vehiculo: float
    cuota_inicial: float
    porcentaje_cuota_inicial: float
    cuota_final: float
    monto_financiado: float
    plazo_meses: int
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    tea_equivalente: float
    tem: float
    tipo_gracia: TipoGracia
    meses_gracia: int
    cuota_mensual: float
    cuota_total_promedio: float
    total_intereses: float
    total_amortizado: float
    total_seguros: float
    total_gastos_iniciales: float
    total_cargos_desembolso: float
    total_gps_mantenimiento: float
    costo_total_credito: float
    monto_total_pagado: float
    cok_anual: float
    cok_mensual: float
    tasa_descuento_van: float
    van: float
    tir_mensual: float | None
    tir_anual: float | None
    tcea: float | None


class ResultadoCalculo(IndicadoresSimulacion):
    """Resultado del calculo de previsualizacion: indicadores y cronograma."""

    cronograma: list[CronogramaFilaRespuesta]


class SimulacionRespuesta(BaseModel):
    """Representacion completa de una simulacion persistida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str | None
    cliente_id: int
    vehiculo_id: int
    usuario_id: int
    estado: EstadoSimulacion
    moneda: Moneda
    tipo_cambio_referencial: float | None
    precio_vehiculo: float
    cuota_inicial: float
    porcentaje_cuota_inicial: float
    monto_financiado: float
    plazo_meses: int
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    tea_equivalente: float
    tem: float
    tipo_gracia: TipoGracia
    meses_gracia: int
    fecha_inicio: date
    porcentaje_cuota_final: float
    cuota_final: float
    seguro_desgravamen_anual: float
    desgravamen_consentido: bool
    seguro_vehicular_mensual: float
    gps_instalacion: float
    gps_mantenimiento_mensual: float
    gps_reposicion: float
    gastos_notariales: float
    gastos_registrales: float
    tasacion: float
    gastos_iniciales: float
    cok_anual: float
    tasa_descuento_van: float
    tasa_moratoria_anual: float
    aseguradora: str | None
    numero_poliza: str | None
    coberturas: str | None
    cuota_mensual: float
    cuota_total_promedio: float
    van: float
    tir_mensual: float | None
    tir_anual: float | None
    tcea: float | None
    costo_total_credito: float
    total_intereses: float
    total_amortizado: float
    total_seguros: float
    total_cargos_desembolso: float
    total_gps_mantenimiento: float
    monto_total_pagado: float
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SimulacionDetalle(SimulacionRespuesta):
    """Simulacion con datos descriptivos y cronograma asociado."""

    cliente_nombre: str | None = None
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
    cliente_id: int
    vehiculo_id: int
    cliente_nombre: str | None = None
    vehiculo_descripcion: str | None = None
    monto_financiado: float
    plazo_meses: int
    cuota_mensual: float
    tcea: float | None
    fecha_creacion: datetime
