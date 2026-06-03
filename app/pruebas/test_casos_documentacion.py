"""Pruebas de escenarios completos de credito vehicular (metodo frances).

Verifican propiedades estructurales del credito frances vencido ordinario (sin
cuota final) y la correccion del flujo para la TCEA: los gastos iniciales
financiados no son dinero recibido, por lo que elevan la TCEA.
"""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import (
    Capitalizacion,
    Moneda,
    TipoGracia,
    TipoTasa,
)
from app.servicios.servicio_simulacion import EntradaSimulacion, calcular_simulacion


def _entrada_base(**extra) -> EntradaSimulacion:
    datos = dict(
        moneda=Moneda.SOLES,
        precio_vehiculo=Decimal("90000"),
        porcentaje_cuota_inicial=Decimal("0.20"),
        plazo_meses=36,
        tipo_tasa=TipoTasa.EFECTIVA,
        valor_tasa=Decimal("0.15"),
        capitalizacion=None,
        tipo_gracia=TipoGracia.NINGUNA,
        meses_gracia=0,
        porcentaje_cuota_final=Decimal("0"),
        seguro_desgravamen_anual=Decimal("0.0035"),
        desgravamen_consentido=True,
        seguro_vehicular_mensual=Decimal("250"),
        gps_instalacion=Decimal("800"),
        gastos_notariales=Decimal("1000"),
        cok_anual=Decimal("0.10"),
        fecha_inicio=date(2026, 1, 1),
    )
    datos.update(extra)
    return EntradaSimulacion(**datos)


def test_credito_soles_tea_sin_gracia():
    """Credito en soles, TEA 15%, sin gracia: frances clasico que termina en cero."""

    resultado = calcular_simulacion(_entrada_base())

    # monto_financiado = precio - cuota_inicial + gastos_iniciales financiados.
    assert resultado.monto_financiado == Decimal("73000")  # 90000 - 18000 + 1000
    assert len(resultado.filas) == 36
    # La TEM equivalente de una TEA de 15%.
    assert abs(resultado.tem - Decimal("0.0117149")) < Decimal("1e-6")
    # La cuota ordinaria es constante en los periodos regulares (metodo frances).
    cuotas = {round(float(fila.cuota_ordinaria), 2) for fila in resultado.filas[:-1]}
    assert len(cuotas) == 1
    assert resultado.cuota_mensual > 0
    # El saldo llega exactamente a cero.
    assert resultado.filas[-1].saldo_final == Decimal("0")
    # La TCEA refleja seguros y GPS, por lo que supera a la TEA.
    assert resultado.tcea is not None and resultado.tcea > resultado.tea_equivalente


def test_credito_dolares_tna_gracia_parcial():
    """Credito en dolares, TNA 12% mensual, con gracia parcial de 3 meses."""

    resultado = calcular_simulacion(
        _entrada_base(
            moneda=Moneda.DOLARES,
            precio_vehiculo=Decimal("35000"),
            plazo_meses=48,
            tipo_tasa=TipoTasa.NOMINAL,
            valor_tasa=Decimal("0.12"),
            capitalizacion=Capitalizacion.MENSUAL,
            tipo_gracia=TipoGracia.PARCIAL,
            meses_gracia=3,
            seguro_desgravamen_anual=Decimal("0.0045"),
            seguro_vehicular_mensual=Decimal("60"),
            gps_instalacion=Decimal("250"),
            gastos_notariales=Decimal("500"),
        )
    )

    assert resultado.monto_financiado == Decimal("28500")  # 35000 - 7000 + 500
    assert abs(resultado.tem - Decimal("0.01")) < Decimal("1e-7")  # TNA 12%/12 = 1%
    # Durante la gracia parcial solo se paga el interes y el saldo no varia.
    assert resultado.filas[0].amortizacion == Decimal("0")
    assert resultado.filas[0].saldo_final == resultado.filas[0].saldo_inicial
    assert resultado.filas[-1].saldo_final == Decimal("0")
    assert resultado.tcea is not None


def test_gastos_iniciales_financiados_elevan_la_tcea():
    """Los gastos iniciales financiados no son dinero recibido: suben la TCEA.

    Reproduce la correccion: con gastos iniciales el prestamo (y las cuotas) sube,
    pero el desembolso neto del periodo 0 no los incluye, por lo que la TCEA crece.
    """

    sin_gastos = calcular_simulacion(_entrada_base(gastos_notariales=Decimal("0")))
    con_gastos = calcular_simulacion(_entrada_base(gastos_notariales=Decimal("1000")))

    assert con_gastos.monto_financiado > sin_gastos.monto_financiado
    assert con_gastos.tcea is not None and sin_gastos.tcea is not None
    assert con_gastos.tcea > sin_gastos.tcea
