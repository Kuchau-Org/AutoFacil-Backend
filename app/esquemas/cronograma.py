"""Esquemas Pydantic para las filas del cronograma de pagos."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.modelos.enumeraciones import TipoPeriodo


class CronogramaFilaRespuesta(BaseModel):
    """Detalle de un periodo del cronograma (cuoton, cuota regular y flujo)."""

    model_config = ConfigDict(from_attributes=True)

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    # Tramo del cuoton.
    saldo_inicial_cuoton: float
    interes_cuoton: float
    amortizacion_cuoton: float
    desgravamen_cuoton: float
    saldo_final_cuoton: float
    # Tramo regular.
    saldo_inicial: float
    interes: float
    cuota: float
    amortizacion: float
    seguro_desgravamen: float
    seguro_riesgo: float
    gps: float
    portes: float
    gastos_adm: float
    saldo_final: float
    flujo: float
