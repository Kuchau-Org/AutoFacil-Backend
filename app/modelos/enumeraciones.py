"""Enumeraciones de dominio."""

from enum import Enum


class Moneda(str, Enum):
    """Monedas admitidas para precios y simulaciones."""

    SOLES = "PEN"
    DOLARES = "USD"


class TipoTasa(str, Enum):
    """Tipo de tasa de interes ingresada (TNA = nominal, TEA = efectiva)."""

    NOMINAL = "NOMINAL"
    EFECTIVA = "EFECTIVA"


class Capitalizacion(str, Enum):
    """Frecuencias de capitalizacion admitidas para una tasa nominal (TNA).

    El modelo del Excel solo contempla capitalizacion diaria o mensual.
    """

    DIARIA = "DIARIA"
    MENSUAL = "MENSUAL"


class Plan(str, Enum):
    """Plan de pagos: define el numero de cuotas y el porcentaje de cuota final."""

    PLAN_24 = "PLAN_24"
    PLAN_36 = "PLAN_36"

    @property
    def numero_cuotas(self) -> int:
        return 24 if self is Plan.PLAN_24 else 36

    @property
    def numero_anios(self) -> int:
        return 2 if self is Plan.PLAN_24 else 3

    @property
    def porcentaje_cuota_final(self) -> str:
        return "0.50" if self is Plan.PLAN_24 else "0.40"


class TipoPeriodo(str, Enum):
    """Clasificacion de cada fila del cronograma de pagos."""

    GRACIA_TOTAL = "GRACIA_TOTAL"
    GRACIA_PARCIAL = "GRACIA_PARCIAL"
    CUOTA_ORDINARIA = "CUOTA_ORDINARIA"
    CUOTA_FINAL = "CUOTA_FINAL"


class EstadoSimulacion(str, Enum):
    """Estado de una simulacion: vigente (CALCULADA) o archivada (ARCHIVADA)."""

    CALCULADA = "CALCULADA"
    ARCHIVADA = "ARCHIVADA"
