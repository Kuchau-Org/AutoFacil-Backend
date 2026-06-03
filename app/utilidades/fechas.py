"""Utilidades de fechas basadas en el calendario comercial de 30 dias.

El modelo financiero del proyecto trabaja con meses comerciales de 30 dias y
anio financiero de 360 dias. El cronograma de pagos avanza periodos de 30 dias
exactos desde la fecha de desembolso, de modo que la fecha mostrada en cada
cuota es coherente con la convencion de 30 dias usada para los intereses.
"""

from datetime import date, timedelta

DIAS_MES_COMERCIAL = 30
DIAS_ANIO_COMERCIAL = 360


def avanzar_periodos_comerciales(fecha_base: date, periodos: int) -> date:
    """Avanza `periodos` meses comerciales (de 30 dias) desde la fecha base."""

    return fecha_base + timedelta(days=DIAS_MES_COMERCIAL * periodos)


def formato_dia_mes_anio(fecha: date) -> str:
    """Formatea una fecha en el formato dia/mes/anio usado en la interfaz."""

    return fecha.strftime("%d/%m/%Y")
