"""Servicio de calculo de la TCEA (Tasa de Costo Efectivo Anual).

La TCEA refleja el costo real anual del financiamiento e incluye, ademas del
interes, los seguros, el GPS y los gastos iniciales. Siguiendo la definicion de la SBS, la TCEA es la tasa que
iguala el importe desembolsado con el valor presente de todos los pagos del
deudor; es decir, equivale a la tasa interna de retorno del flujo de costos
del deudor, anualizada de forma compuesta.
"""

from decimal import Decimal

from app.servicios.servicio_van_tir import calcular_tir
from app.utilidades.decimales import MESES_ANIO, UNO, potencia


def calcular_tcea(flujos_costo_deudor: list[Decimal]) -> tuple[Decimal | None, Decimal | None]:
    """Calcula la tasa mensual equivalente de costo y la TCEA anual.

    Recibe el flujo de costos del deudor (desembolso neto positivo en el
    periodo 0 y pagos negativos en los periodos siguientes). Devuelve la tupla
    (tasa_mensual_equivalente, tcea_anual). Si no es posible determinar la tasa
    devuelve (None, None).
    """

    tasa_mensual = calcular_tir(flujos_costo_deudor)
    if tasa_mensual is None:
        return None, None

    tcea_anual = potencia(UNO + tasa_mensual, MESES_ANIO) - UNO
    return tasa_mensual, tcea_anual
