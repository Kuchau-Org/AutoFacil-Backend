"""Esquemas Pydantic para las filas del cronograma de pagos."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.modelos.enumeraciones import TipoPeriodo


class CronogramaFilaRespuesta(BaseModel):
    """Detalle de un periodo del cronograma para la interfaz."""

    model_config = ConfigDict(from_attributes=True)

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    saldo_inicial: float
    interes: float
    amortizacion: float
    seguro_desgravamen: float
    seguro_vehicular: float
    gps_mantenimiento: float
    cuota_ordinaria: float
    cuota_final_extraordinaria: float
    cuota_total: float
    saldo_final: float
