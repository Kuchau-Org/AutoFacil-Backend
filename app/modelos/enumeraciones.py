"""Enumeraciones de dominio compartidas por modelos, esquemas y servicios.

Centralizar los valores admitidos evita inconsistencias entre la capa de
persistencia, la validacion de entrada y la logica financiera.
"""

from enum import Enum


class Moneda(str, Enum):
    """Monedas admitidas para precios, configuraciones y simulaciones."""

    SOLES = "PEN"
    DOLARES = "USD"


class TipoTasa(str, Enum):
    """Tipo de tasa de interes ingresada por el analista."""

    EFECTIVA = "EFECTIVA"
    NOMINAL = "NOMINAL"


class Capitalizacion(str, Enum):
    """Frecuencias de capitalizacion admitidas para tasas nominales."""

    DIARIA = "DIARIA"
    MENSUAL = "MENSUAL"
    BIMESTRAL = "BIMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    CUATRIMESTRAL = "CUATRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"


class TipoGracia(str, Enum):
    """Tipos de periodo de gracia configurables al inicio del credito."""

    NINGUNA = "NINGUNA"
    TOTAL = "TOTAL"
    PARCIAL = "PARCIAL"


class TipoPeriodo(str, Enum):
    """Clasificacion de cada fila del cronograma de pagos."""

    GRACIA_TOTAL = "GRACIA_TOTAL"
    GRACIA_PARCIAL = "GRACIA_PARCIAL"
    CUOTA_ORDINARIA = "CUOTA_ORDINARIA"
    CUOTA_FINAL = "CUOTA_FINAL"


class EstadoSimulacion(str, Enum):
    """Estados de una simulacion. AutoFacil es un simulador de propuestas, no un
    sistema de aprobacion: por eso solo distingue una propuesta vigente
    (CALCULADA) de una archivada (ARCHIVADA, baja logica que conserva el
    historial)."""

    CALCULADA = "CALCULADA"
    ARCHIVADA = "ARCHIVADA"
