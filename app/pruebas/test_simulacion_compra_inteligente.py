"""Pruebas de la simulacion completa de credito vehicular (VAN, TIR y TCEA)."""

from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import (
    Capitalizacion,
    Moneda,
    TipoGracia,
    TipoPeriodo,
    TipoTasa,
)
from app.servicios import servicio_van_tir
from app.servicios.servicio_simulacion import (
    EntradaSimulacion,
    calcular_simulacion,
    redondear_resultado,
)
from app.servicios.servicio_tcea import calcular_tcea

TOLERANCIA = Decimal("1e-6")


def _entrada_base(**cambios) -> EntradaSimulacion:
    """Construye una entrada de simulacion estandar para las pruebas."""

    parametros = dict(
        moneda=Moneda.SOLES,
        precio_vehiculo=Decimal("80000"),
        porcentaje_cuota_inicial=Decimal("0.20"),
        plazo_meses=48,
        tipo_tasa=TipoTasa.EFECTIVA,
        valor_tasa=Decimal("0.145"),
        capitalizacion=None,
        tipo_gracia=TipoGracia.NINGUNA,
        meses_gracia=0,
        porcentaje_cuota_final=Decimal("0"),
        seguro_desgravamen_anual=Decimal("0.006"),
        desgravamen_consentido=True,
        seguro_vehicular_mensual=Decimal("85"),
        gps_instalacion=Decimal("30"),
        gps_mantenimiento_mensual=Decimal("0"),
        gastos_notariales=Decimal("350"),
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


def test_simulacion_completa_saldo_final_cero():
    """La simulacion completa (frances) debe terminar con saldo final cero."""

    resultado = calcular_simulacion(_entrada_base())

    # 80000 - 20% + gastos iniciales financiados (350).
    assert resultado.monto_financiado == Decimal("64350")
    assert resultado.filas[-1].saldo_final == Decimal("0")
    # La cuota ordinaria es constante en los periodos regulares (metodo frances).
    cuotas = {round(float(fila.cuota_ordinaria), 2) for fila in resultado.filas[:-1]}
    assert len(cuotas) == 1


def test_simulacion_indicadores_presentes():
    """La simulacion debe devolver VAN, TIR y TCEA calculables."""

    resultado = calcular_simulacion(_entrada_base())

    assert resultado.van is not None
    assert resultado.tir_mensual is not None
    assert resultado.tir_anual is not None
    assert resultado.tcea is not None
    # La TCEA equivale a la TIR anualizada del flujo de costos del deudor.
    assert abs(resultado.tcea - resultado.tir_anual) < Decimal("1e-9")
    # Con seguros y gastos, la TCEA debe superar a la TEA del credito.
    assert resultado.tcea > resultado.tea_equivalente


def test_simulacion_gracia_total_saldo_cero():
    """La simulacion con gracia total tambien debe cerrar en saldo cero."""

    resultado = calcular_simulacion(
        _entrada_base(tipo_gracia=TipoGracia.TOTAL, meses_gracia=3)
    )
    assert resultado.meses_gracia == 3
    assert resultado.filas[-1].saldo_final == Decimal("0")


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


def test_cuota_balon_difiere_valor_futuro_y_cierra_en_cero():
    """Con cuota balon, el saldo termina en cero y la ultima cuota lleva el balon."""

    base = calcular_simulacion(_entrada_base())
    con_balon = calcular_simulacion(_entrada_base(porcentaje_cuota_final=Decimal("0.40")))

    # La cuota balon es el 40% del precio del vehiculo (valor futuro).
    assert con_balon.cuota_final == Decimal("80000") * Decimal("0.40")
    # La ultima fila es la cuota con balon y deja el saldo en cero.
    assert con_balon.filas[-1].tipo_periodo == TipoPeriodo.CUOTA_FINAL
    assert con_balon.filas[-1].cuota_final_extraordinaria > Decimal("0")
    assert con_balon.filas[-1].saldo_final == Decimal("0")
    # Diferir parte del capital reduce la cuota ordinaria mensual.
    assert con_balon.cuota_mensual < base.cuota_mensual


def test_gps_instalacion_es_cargo_al_desembolso():
    """La instalacion del GPS es un cargo unico al desembolso que eleva la TCEA."""

    sin = calcular_simulacion(_entrada_base(gps_instalacion=Decimal("0")))
    con = calcular_simulacion(_entrada_base(gps_instalacion=Decimal("250")))
    assert sin.total_cargos_desembolso == Decimal("0")
    assert con.total_cargos_desembolso == Decimal("250")
    assert con.tcea > sin.tcea


def test_redondeo_balon_con_gracia_total_muestra_valor_contractual():
    """Con gracia total, la cuota balon mostrada conserva su valor contractual.

    La reconciliacion de redondeo NO debe forzar la suma de amortizaciones al
    monto financiado (en gracia total se capitalizan intereses) ni recortar la
    cuota balon: esta se muestra como el porcentaje del precio pactado.
    """

    resultado = calcular_simulacion(
        _entrada_base(
            precio_vehiculo=Decimal("80000"),
            porcentaje_cuota_inicial=Decimal("0"),
            porcentaje_cuota_final=Decimal("0.40"),
            tipo_gracia=TipoGracia.TOTAL,
            meses_gracia=3,
            seguro_desgravamen_anual=Decimal("0"),
            desgravamen_consentido=False,
            seguro_vehicular_mensual=Decimal("0"),
            gps_instalacion=Decimal("0"),
            gastos_notariales=Decimal("0"),
        )
    )
    crono = redondear_resultado(resultado)["cronograma"]
    # La cuota balon es exactamente el 40% del precio (80000), no un valor recortado.
    assert crono[-1]["cuota_final_extraordinaria"] == Decimal("32000.00")
    assert crono[-1]["saldo_final"] == Decimal("0.00")
    # Ninguna cuota balon puede ser negativa por arrastre de redondeo.
    assert all(fila["cuota_final_extraordinaria"] >= Decimal("0") for fila in crono)


def test_sin_balon_no_genera_cuota_final_negativa():
    """Sin cuota balon, el pago final extraordinario es exactamente cero."""

    crono = redondear_resultado(calcular_simulacion(_entrada_base()))["cronograma"]
    assert crono[-1]["cuota_final_extraordinaria"] == Decimal("0.00")
    assert all(fila["cuota_final_extraordinaria"] >= Decimal("0") for fila in crono)


def test_cuota_total_promedio_excluye_la_balon():
    """El promedio mensual refleja la cuota regular, no la cuota balon final."""

    con_balon = calcular_simulacion(_entrada_base(porcentaje_cuota_final=Decimal("0.40")))
    ultima = con_balon.filas[-1]
    # La ultima cuota total incluye la balon; el promedio mensual no.
    assert con_balon.cuota_total_promedio < ultima.cuota_total
    assert con_balon.cuota_total_promedio < con_balon.cuota_final


def test_gastos_terceros_financiados_elevan_la_tcea():
    """Los gastos de terceros financiados se suman al monto y elevan la TCEA."""

    base = calcular_simulacion(
        _entrada_base(gps_instalacion=Decimal("0"), gastos_notariales=Decimal("0"))
    )
    con_gastos = calcular_simulacion(
        _entrada_base(gps_instalacion=Decimal("0"), gastos_notariales=Decimal("1000"))
    )
    assert con_gastos.total_gastos_iniciales == Decimal("1000")
    assert con_gastos.monto_financiado == base.monto_financiado + Decimal("1000")
    # Al financiarse (y no recibirse en efectivo), elevan la TCEA.
    assert con_gastos.tcea > base.tcea


def test_gps_reposicion_no_se_cobra_al_contratar():
    """La reposicion de GPS es contingente (tarifario): no se cobra ni afecta la TCEA."""

    sin = calcular_simulacion(
        _entrada_base(gps_instalacion=Decimal("250"), gps_reposicion=Decimal("0"))
    )
    con = calcular_simulacion(
        _entrada_base(gps_instalacion=Decimal("250"), gps_reposicion=Decimal("120"))
    )
    # Solo la instalacion entra al desembolso; la reposicion no cambia nada.
    assert sin.total_cargos_desembolso == Decimal("250")
    assert con.total_cargos_desembolso == Decimal("250")
    assert con.tcea == sin.tcea


def test_desgravamen_sin_consentimiento_no_se_cobra():
    """Sin consentimiento, el desgravamen no se cobra aunque se indique una tasa."""

    sin_consentimiento = calcular_simulacion(
        _entrada_base(seguro_desgravamen_anual=Decimal("0.006"), desgravamen_consentido=False)
    )
    con_consentimiento = calcular_simulacion(
        _entrada_base(seguro_desgravamen_anual=Decimal("0.006"), desgravamen_consentido=True)
    )
    desgravamen_sin = sum(fila.seguro_desgravamen for fila in sin_consentimiento.filas)
    assert desgravamen_sin == Decimal("0")
    assert con_consentimiento.total_seguros > sin_consentimiento.total_seguros
