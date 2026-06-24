"""Calculo de la TCEA (TIR del flujo del deudor anualizada de forma compuesta)."""

from decimal import Decimal

from app.servicios.servicio_van_tir import calcular_tir
from app.utilidades.decimales import MESES_ANIO, UNO, potencia


def calcular_tcea(flujos_costo_deudor: list[Decimal]) -> tuple[Decimal | None, Decimal | None]:
    """Devuelve (tasa mensual de costo, TCEA anual) o (None, None)."""

    tasa_mensual = calcular_tir(flujos_costo_deudor)
    if tasa_mensual is None:
        return None, None

    tcea_anual = potencia(UNO + tasa_mensual, MESES_ANIO) - UNO
    return tasa_mensual, tcea_anual
