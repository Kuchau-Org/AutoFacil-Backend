"""Test maestro: reproduce EXACTO el modelo Excel "Compra Inteligente".

Los valores esperados provienen del modelo del profesor (Plan 36, TNA 15% con
capitalizacion diaria, gracia 3 meses total + 3 parcial). Si el motor coincide
con estos numeros, replica fielmente la hoja de calculo.
"""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import Capitalizacion, Moneda, Plan, TipoPeriodo, TipoTasa
from app.servicios.servicio_simulacion import (
    CostoInicial,
    EntradaSimulacion,
    calcular_simulacion,
)

# Tolerancias: dos decimales para importes, alta precision para tasas.
TOL_MONTO = Decimal("0.01")
TOL_TASA = Decimal("1e-6")


def _entrada_maestra() -> EntradaSimulacion:
    return EntradaSimulacion(
        moneda=Moneda.SOLES,
        precio_vehiculo=Decimal("16000"),
        plan=Plan.PLAN_36,
        porcentaje_cuota_inicial=Decimal("0.20"),
        tipo_tasa=TipoTasa.NOMINAL,
        valor_tasa=Decimal("0.15"),
        capitalizacion=Capitalizacion.DIARIA,
        meses_gracia_total=3,
        meses_gracia_parcial=3,
        costo_notarial=CostoInicial(Decimal("100"), True),
        costo_registral=CostoInicial(Decimal("75"), True),
        gps_periodico=Decimal("20"),
        portes_periodico=Decimal("3.5"),
        gastos_adm_periodico=Decimal("3.5"),
        seguro_desgravamen_mensual=Decimal("0.00049"),
        seguro_riesgo_anual=Decimal("0.003"),
        cok_anual=Decimal("0.50"),
        fecha_inicio=date(2026, 1, 1),
    )


def test_indicadores_coinciden_con_el_excel():
    """TEA, TEM, montos base e indicadores de rentabilidad replican el Excel."""

    r = calcular_simulacion(_entrada_maestra())
    assert abs(r.tea_equivalente - Decimal("0.161797946")) < TOL_TASA
    assert abs(r.tem - Decimal("0.012575815")) < TOL_TASA
    assert r.cuota_inicial == Decimal("3200")
    assert r.cuota_final == Decimal("6400")
    assert r.monto_prestamo == Decimal("12975")
    assert abs(r.saldo_financiado - Decimal("9015.99")) < TOL_MONTO
    assert abs(r.seguro_riesgo_periodico - Decimal("4.00")) < TOL_MONTO
    assert abs(r.cuota_mensual - Decimal("379.16")) < TOL_MONTO
    assert abs(r.cok_mensual - Decimal("0.0343661")) < TOL_TASA
    assert abs(r.tir_mensual - Decimal("0.0158617")) < TOL_TASA
    assert abs(r.tcea - Decimal("0.2078564")) < TOL_TASA
    assert abs(r.van - Decimal("4436.18")) < TOL_MONTO


def test_totales_coinciden_con_el_excel():
    """Los totales desagregados (transparencia) replican el Excel."""

    r = calcular_simulacion(_entrada_maestra())
    assert abs(r.total_intereses - Decimal("2264.74")) < TOL_MONTO
    assert abs(r.total_amortizado - Decimal("15760.44")) < TOL_MONTO
    assert abs(r.total_seguro_desgravamen - Decimal("102.72")) < TOL_MONTO
    assert abs(r.total_seguro_riesgo - Decimal("148.00")) < TOL_MONTO
    assert abs(r.total_gps - Decimal("740.00")) < TOL_MONTO
    assert abs(r.total_portes - Decimal("129.50")) < TOL_MONTO
    assert abs(r.total_gastos_adm - Decimal("129.50")) < TOL_MONTO


def test_estructura_cronograma_coincide_con_el_excel():
    """37 periodos, gracia 3T+3P, cuoton pagado en N+1 y saldos en cero."""

    r = calcular_simulacion(_entrada_maestra())
    assert len(r.filas) == 37  # N=36 cuotas + el cuoton en el periodo 37

    # Gracia: 3 meses total y luego 3 parcial.
    assert [f.tipo_periodo for f in r.filas[:3]] == [TipoPeriodo.GRACIA_TOTAL] * 3
    assert [f.tipo_periodo for f in r.filas[3:6]] == [TipoPeriodo.GRACIA_PARCIAL] * 3
    assert r.filas[6].tipo_periodo == TipoPeriodo.CUOTA_ORDINARIA

    # Periodo 1 (gracia total): el cuoton arranca en su valor presente.
    assert abs(r.filas[0].saldo_inicial_cuoton - Decimal("3959.01")) < TOL_MONTO
    assert abs(r.filas[0].saldo_inicial - Decimal("9015.99")) < TOL_MONTO
    assert abs(r.filas[0].flujo - Decimal("-35.42")) < TOL_MONTO

    # Periodo 7 (primera cuota ordinaria).
    assert abs(r.filas[6].cuota - Decimal("379.16")) < TOL_MONTO
    assert abs(r.filas[6].amortizacion - Decimal("256.86")) < TOL_MONTO
    assert abs(r.filas[6].flujo - Decimal("-410.16")) < TOL_MONTO

    # Periodo 37: se cancela el cuoton (= cuota final) y todo cierra en cero.
    ultima = r.filas[-1]
    assert ultima.tipo_periodo == TipoPeriodo.CUOTA_FINAL
    assert abs(ultima.amortizacion_cuoton - Decimal("6400.00")) < TOL_MONTO
    assert abs(ultima.flujo - Decimal("-6431.00")) < TOL_MONTO
    assert abs(ultima.saldo_final_cuoton) < TOL_MONTO
    assert abs(r.filas[35].saldo_final) < TOL_MONTO  # saldo regular en cero en N


def test_plan_24_difiere_cuoton_en_periodo_25():
    """Plan 24: 24 cuotas, cuota final 50% y cuoton en el periodo 25."""

    entrada = _entrada_maestra()
    entrada.plan = Plan.PLAN_24
    r = calcular_simulacion(entrada)
    assert r.numero_cuotas == 24
    assert r.porcentaje_cuota_final == Decimal("0.50")
    assert r.cuota_final == Decimal("16000") * Decimal("0.50")
    assert len(r.filas) == 25
    assert r.filas[-1].tipo_periodo == TipoPeriodo.CUOTA_FINAL
    assert abs(r.filas[-1].saldo_final_cuoton) < TOL_MONTO


def test_costo_en_efectivo_no_eleva_el_prestamo():
    """Un costo marcado al contado (efectivo) no se suma al prestamo."""

    entrada = _entrada_maestra()
    entrada.costo_notarial = CostoInicial(Decimal("100"), False)  # ahora al contado
    r = calcular_simulacion(entrada)
    # Prestamo = 16000 - 3200 + 75 (solo registrales financiados) = 12875.
    assert r.monto_prestamo == Decimal("12875")
    assert r.total_costos_efectivo == Decimal("100")
    assert r.total_costos_financiados == Decimal("75")
