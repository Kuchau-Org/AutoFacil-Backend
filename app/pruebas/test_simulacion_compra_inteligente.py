"""Pruebas de la simulacion completa de credito vehicular (VAN, TIR y TCEA)."""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import Capitalizacion, Moneda, Plan, TipoPeriodo, TipoTasa
from app.servicios import servicio_van_tir
from app.servicios.servicio_simulacion import (
    CostoInicial,
    EntradaSimulacion,
    calcular_simulacion,
    redondear_resultado,
)
from app.servicios.servicio_tcea import calcular_tcea


def _entrada_base(**cambios) -> EntradaSimulacion:
    """Construye una entrada de simulacion estandar para las pruebas."""

    parametros = dict(
        moneda=Moneda.SOLES,
        precio_vehiculo=Decimal("80000"),
        plan=Plan.PLAN_36,
        porcentaje_cuota_inicial=Decimal("0.20"),
        tipo_tasa=TipoTasa.EFECTIVA,
        valor_tasa=Decimal("0.145"),
        capitalizacion=None,
        meses_gracia_total=0,
        meses_gracia_parcial=0,
        gps_periodico=Decimal("20"),
        portes_periodico=Decimal("5"),
        gastos_adm_periodico=Decimal("5"),
        seguro_desgravamen_mensual=Decimal("0.0005"),
        seguro_riesgo_anual=Decimal("0.003"),
        cok_anual=Decimal("0.12"),
        fecha_inicio=date(2026, 1, 1),
    )
    parametros.update(cambios)
    return EntradaSimulacion(**parametros)


def test_van_flujos_conocidos():
    """El VAN de un flujo conocido debe coincidir con el calculo manual."""

    flujos = [Decimal("-1000"), Decimal("600"), Decimal("600")]
    van = servicio_van_tir.calcular_van(flujos, Decimal("0.10"))
    # -1000 + 600/1.1 + 600/1.21
    assert abs(van - Decimal("41.32231405")) < Decimal("1e-6")


def test_tir_flujos_conocidos():
    """La TIR de un flujo conocido debe anular el VAN a esa tasa."""

    flujos = [Decimal("-1000"), Decimal("600"), Decimal("600")]
    tir = servicio_van_tir.calcular_tir(flujos)
    assert tir is not None
    assert abs(tir - Decimal("0.130662386")) < Decimal("1e-6")
    assert abs(servicio_van_tir.calcular_van(flujos, tir)) < Decimal("1e-6")


def test_tcea_anualiza_la_tasa_mensual():
    """La TCEA debe ser la anualizacion compuesta de la tasa mensual de costo."""

    flujos = [Decimal("2647.13")] + [Decimal("-900")] * 3
    tasa_mensual, tcea = calcular_tcea(flujos)
    assert tasa_mensual is not None and tcea is not None
    esperado = (Decimal("1") + tasa_mensual) ** 12 - Decimal("1")
    assert abs(tcea - esperado) < Decimal("1e-9")


def test_simulacion_completa_cierra_en_cero():
    """La simulacion debe cerrar el saldo regular y el cuoton en cero."""

    resultado = calcular_simulacion(_entrada_base())
    assert len(resultado.filas) == 37  # 36 cuotas + cuoton
    # El cuoton es el 40% del precio (Plan 36).
    assert resultado.cuota_final == Decimal("80000") * Decimal("0.40")
    assert resultado.monto_prestamo == Decimal("64000")  # 80000 - 20%
    assert abs(resultado.filas[35].saldo_final) < Decimal("1e-6")
    assert abs(resultado.filas[-1].saldo_final_cuoton) < Decimal("1e-6")
    # La cuota regular es constante en los periodos ordinarios.
    ordinarias = {
        round(float(f.cuota), 2)
        for f in resultado.filas
        if f.tipo_periodo == TipoPeriodo.CUOTA_ORDINARIA
    }
    assert len(ordinarias) == 1


def test_simulacion_indicadores_presentes():
    """La simulacion debe devolver VAN, TIR y TCEA calculables."""

    resultado = calcular_simulacion(_entrada_base())
    assert resultado.van is not None
    assert resultado.tir_mensual is not None and resultado.tir_anual is not None
    assert resultado.tcea is not None
    # La TCEA equivale a la TIR anualizada del flujo de costos del deudor.
    assert abs(resultado.tcea - resultado.tir_anual) < Decimal("1e-9")
    # Con seguros y gastos, la TCEA debe superar a la TEA del credito.
    assert resultado.tcea > resultado.tea_equivalente


def test_simulacion_gracia_total_cierra_en_cero():
    """La simulacion con gracia total tambien debe cerrar en saldo cero."""

    resultado = calcular_simulacion(_entrada_base(meses_gracia_total=3))
    assert resultado.meses_gracia_total == 3
    assert [f.tipo_periodo for f in resultado.filas[:3]] == [TipoPeriodo.GRACIA_TOTAL] * 3
    assert abs(resultado.filas[35].saldo_final) < Decimal("1e-6")
    assert abs(resultado.filas[-1].saldo_final_cuoton) < Decimal("1e-6")


def test_simulacion_tasa_nominal():
    """La simulacion debe admitir tasa nominal con capitalizacion mensual."""

    resultado = calcular_simulacion(
        _entrada_base(
            tipo_tasa=TipoTasa.NOMINAL,
            valor_tasa=Decimal("0.12"),
            capitalizacion=Capitalizacion.MENSUAL,
        )
    )
    assert abs(resultado.tem - Decimal("0.01")) < Decimal("1e-10")


def test_plan_24_usa_cuota_final_del_50_por_ciento():
    """El Plan 24 difiere el 50% del precio al cuoton y usa 24 cuotas."""

    resultado = calcular_simulacion(_entrada_base(plan=Plan.PLAN_24))
    assert resultado.numero_cuotas == 24
    assert resultado.cuota_final == Decimal("80000") * Decimal("0.50")
    assert len(resultado.filas) == 25


def test_costos_financiados_elevan_el_prestamo_y_la_cuota():
    """Los costos financiados se suman al prestamo (que el deudor recibe en t0) y
    elevan la cuota mensual."""

    base = calcular_simulacion(_entrada_base())
    con_costos = calcular_simulacion(
        _entrada_base(costo_notarial=CostoInicial(Decimal("1000"), True))
    )
    assert con_costos.total_costos_financiados == Decimal("1000")
    assert con_costos.monto_prestamo == base.monto_prestamo + Decimal("1000")
    # Mas prestamo => mayor cuota mensual.
    assert con_costos.cuota_mensual > base.cuota_mensual


def test_costo_efectivo_no_eleva_el_prestamo():
    """Un costo al contado no entra al prestamo (no cambia las cuotas)."""

    base = calcular_simulacion(_entrada_base())
    con_efectivo = calcular_simulacion(
        _entrada_base(costo_notarial=CostoInicial(Decimal("1000"), False))
    )
    assert con_efectivo.total_costos_efectivo == Decimal("1000")
    assert con_efectivo.monto_prestamo == base.monto_prestamo


def test_redondeo_cronograma_devuelve_todas_las_filas():
    """El redondeo de presentacion conserva las N+1 filas y el cuoton final."""

    crono = redondear_resultado(calcular_simulacion(_entrada_base()))["cronograma"]
    assert len(crono) == 37
    assert crono[-1]["saldo_final_cuoton"] == Decimal("0.00")
    assert crono[-1]["amortizacion_cuoton"] > Decimal("0")
