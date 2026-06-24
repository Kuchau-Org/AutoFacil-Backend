"""Pruebas del cronograma de pagos (cuota regular + cuoton diferido)."""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoPeriodo
from app.servicios.calculadora_financiera import (
    ParametrosCronograma,
    calcular_cuota_francesa,
    generar_cronograma,
)

TOLERANCIA = Decimal("1e-6")


def _parametros(
    meses_gracia_total: int = 0,
    meses_gracia_parcial: int = 0,
    seguro_desgravamen_mensual: Decimal = Decimal("0"),
    cuota_final: Decimal = Decimal("4000"),
) -> ParametrosCronograma:
    """Construye parametros de cronograma para los escenarios de prueba."""

    return ParametrosCronograma(
        monto_prestamo=Decimal("10000"),
        cuota_final=cuota_final,
        tem=Decimal("0.01"),
        numero_cuotas=12,
        meses_gracia_total=meses_gracia_total,
        meses_gracia_parcial=meses_gracia_parcial,
        seguro_desgravamen_mensual=seguro_desgravamen_mensual,
        seguro_riesgo_periodico=Decimal("0"),
        gps_periodico=Decimal("0"),
        portes_periodico=Decimal("0"),
        gastos_adm_periodico=Decimal("0"),
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


def test_cronograma_tiene_un_periodo_extra_para_el_cuoton():
    """El cronograma tiene N+1 filas: las N cuotas y el cuoton en el periodo N+1."""

    resultado = generar_cronograma(_parametros())
    assert len(resultado.filas) == 13  # 12 cuotas + cuoton
    assert resultado.filas[-1].numero_periodo == 13
    assert resultado.filas[-1].tipo_periodo == TipoPeriodo.CUOTA_FINAL
    # El saldo regular cierra en cero en la ultima cuota (N) y el cuoton en N+1.
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA
    assert abs(resultado.filas[-1].saldo_final_cuoton) < TOLERANCIA


def test_cuoton_se_paga_integro_en_el_periodo_final():
    """En el periodo N+1 se cancela el cuoton (sin desgravamen, = cuota final)."""

    resultado = generar_cronograma(_parametros(cuota_final=Decimal("4000")))
    ultima = resultado.filas[-1]
    assert abs(ultima.amortizacion_cuoton - Decimal("4000")) < TOLERANCIA
    # Las cuotas regulares no amortizan el cuoton (solo el saldo financiado).
    assert all(f.amortizacion_cuoton == Decimal("0") for f in resultado.filas[:-1])


def test_saldo_financiado_excluye_el_valor_presente_del_cuoton():
    """El tramo regular amortiza solo el saldo (prestamo menos VP del cuoton)."""

    resultado = generar_cronograma(_parametros(cuota_final=Decimal("4000")))
    # VP del cuoton = 4000 / 1.01^13 ; saldo = 10000 - VP.
    vp = Decimal("4000") / (Decimal("1.01") ** 13)
    assert abs(resultado.saldo_financiado - (Decimal("10000") - vp)) < TOLERANCIA
    assert abs(resultado.filas[0].saldo_inicial - resultado.saldo_financiado) < TOLERANCIA


def test_cronograma_gracia_total_capitaliza_intereses():
    """En la gracia total no hay pago y los intereses se capitalizan al saldo."""

    resultado = generar_cronograma(_parametros(meses_gracia_total=3))
    for fila in resultado.filas[:3]:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_TOTAL
        assert fila.cuota == Decimal("0")
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final > fila.saldo_inicial
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA


def test_cronograma_gracia_parcial_paga_solo_interes():
    """En la gracia parcial solo se paga el interes y el saldo no varia."""

    resultado = generar_cronograma(_parametros(meses_gracia_parcial=2))
    for fila in resultado.filas[:2]:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_PARCIAL
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final == fila.saldo_inicial
        assert abs(fila.cuota - fila.interes) < TOLERANCIA
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA
