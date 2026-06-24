"""Fechas con calendario comercial de 30 dias."""

from datetime import date, timedelta

DIAS_MES_COMERCIAL = 30


def avanzar_periodos_comerciales(fecha_base: date, periodos: int) -> date:
    """Avanza `periodos` meses comerciales (de 30 dias) desde la fecha base."""

    return fecha_base + timedelta(days=DIAS_MES_COMERCIAL * periodos)
