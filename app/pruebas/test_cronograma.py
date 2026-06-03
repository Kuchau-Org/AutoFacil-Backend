"""Pruebas del cronograma de pagos bajo el metodo frances vencido ordinario."""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoGracia, TipoPeriodo
from app.servicios.calculadora_financiera import (
    ParametrosCronograma,
    calcular_cuota_francesa,
    generar_cronograma,
)

TOLERANCIA = Decimal("1e-6")


def _parametros(
    tipo_gracia: TipoGracia = TipoGracia.NINGUNA,
    meses_gracia: int = 0,
    seguro_vehicular_mensual: Decimal = Decimal("0"),
    cuota_final: Decimal = Decimal("0"),
) -> ParametrosCronograma:
    """Construye parametros de cronograma para los escenarios de prueba."""

    return ParametrosCronograma(
        monto_financiado=Decimal("10000"),
        tem=Decimal("0.01"),
        plazo_meses=12,
        tipo_gracia=tipo_gracia,
        meses_gracia=meses_gracia,
        seguro_desgravamen_anual=Decimal("0"),
        seguro_vehicular_mensual=seguro_vehicular_mensual,
        gps_mantenimiento_mensual=Decimal("0"),
        cuota_final=cuota_final,
        fecha_inicio=date(2026, 1, 1),
    )


def test_cuota_francesa_amortiza_hasta_cero():
    """Aplicando la cuota constante, el saldo debe llegar a cero en n periodos."""

    saldo_base = Decimal("10000")
    tasa = Decimal("0.01")
    n = 12
    cuota = calcular_cuota_francesa(saldo_base, tasa, n)

    saldo = saldo_base
    for _ in range(n):
        interes = saldo * tasa
        amortizacion = cuota - interes
        saldo -= amortizacion
    assert abs(saldo) < TOLERANCIA


def test_cuota_francesa_tasa_cero():
    """Con tasa cero la cuota es el saldo repartido en partes iguales."""

    cuota = calcular_cuota_francesa(Decimal("12000"), Decimal("0"), 12)
    assert cuota == Decimal("1000")


def test_cronograma_sin_gracia_llega_a_cero():
    """Un cronograma sin gracia debe terminar con saldo final cero."""

    resultado = generar_cronograma(_parametros())
    assert len(resultado.filas) == 12
    assert resultado.filas[-1].saldo_final == Decimal("0")
    assert resultado.filas[-1].tipo_periodo == TipoPeriodo.CUOTA_ORDINARIA
    # La suma de amortizaciones debe igualar el monto financiado.
    suma_amortizacion = sum(fila.amortizacion for fila in resultado.filas)
    assert abs(suma_amortizacion - Decimal("10000")) < TOLERANCIA


def test_cronograma_gracia_total_capitaliza_intereses():
    """En la gracia total no hay pago y los intereses se capitalizan al saldo."""

    resultado = generar_cronograma(
        _parametros(tipo_gracia=TipoGracia.TOTAL, meses_gracia=3)
    )
    filas_gracia = resultado.filas[:3]
    for fila in filas_gracia:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_TOTAL
        assert fila.cuota_ordinaria == Decimal("0")
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final > fila.saldo_inicial
    # El saldo tras la gracia es el monto capitalizado: 10000 * 1.01^3.
    saldo_esperado = Decimal("10000") * (Decimal("1.01") ** 3)
    assert abs(filas_gracia[-1].saldo_final - saldo_esperado) < TOLERANCIA
    assert resultado.filas[-1].saldo_final == Decimal("0")


def test_cronograma_gracia_parcial_paga_solo_interes():
    """En la gracia parcial solo se paga el interes y el saldo no varia."""

    resultado = generar_cronograma(
        _parametros(tipo_gracia=TipoGracia.PARCIAL, meses_gracia=2)
    )
    filas_gracia = resultado.filas[:2]
    for fila in filas_gracia:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_PARCIAL
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final == fila.saldo_inicial
        assert abs(fila.interes - Decimal("100")) < TOLERANCIA
        assert abs(fila.cuota_ordinaria - Decimal("100")) < TOLERANCIA
    assert resultado.filas[-1].saldo_final == Decimal("0")


def test_cronograma_gracia_total_cobra_seguros():
    """En la gracia total no se amortiza capital, pero los seguros si se cobran."""

    resultado = generar_cronograma(
        _parametros(
            tipo_gracia=TipoGracia.TOTAL,
            meses_gracia=2,
            seguro_vehicular_mensual=Decimal("50"),
        )
    )
    primera = resultado.filas[0]
    assert primera.tipo_periodo == TipoPeriodo.GRACIA_TOTAL
    assert primera.cuota_ordinaria == Decimal("0")
    assert primera.seguro_vehicular == Decimal("50")
    # Aunque no se amortiza ni se paga interes, la cuota total incluye el seguro.
    assert primera.cuota_total == Decimal("50")


def test_cronograma_cuota_balon_deja_saldo_igual_al_balon_antes_del_pago():
    """Con cuota balon, la ultima fila amortiza el saldo y queda en cero."""

    resultado = generar_cronograma(_parametros(cuota_final=Decimal("4000")))
    assert resultado.cuota_final == Decimal("4000")
    ultima = resultado.filas[-1]
    assert ultima.tipo_periodo == TipoPeriodo.CUOTA_FINAL
    assert abs(ultima.cuota_final_extraordinaria - Decimal("4000")) < TOLERANCIA
    assert ultima.saldo_final == Decimal("0")
    # La suma de amortizaciones (incluida la balon) iguala el monto financiado.
    suma_amortizacion = sum(fila.amortizacion for fila in resultado.filas)
    assert abs(suma_amortizacion - Decimal("10000")) < TOLERANCIA
