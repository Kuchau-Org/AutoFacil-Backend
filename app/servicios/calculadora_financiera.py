"""Nucleo de calculo financiero: metodo frances vencido ordinario con cuota balon.

Genera el cronograma de pagos del credito vehicular (producto Compra Inteligente).
Todo el calculo se realiza con `Decimal` de alta precision; no se redondea ningun
valor intermedio. El redondeo se aplica unicamente en la capa de presentacion.

Reglas implementadas:
* Cuotas ordinarias vencidas, una cada periodo comercial de 30 dias.
* La cuota ordinaria del tramo regular es constante y se calcula descontando el
  valor futuro del vehiculo (cuota balon), de modo que el saldo al final del
  plazo sea exactamente ese valor balon.
* La cuota balon se paga junto con la ultima cuota ordinaria y amortiza el saldo
  remanente, llevando el saldo a cero.
* Cada cuota se descompone en interes, amortizacion, seguros (desgravamen y
  vehicular) y el mantenimiento mensual del GPS.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoGracia, TipoPeriodo
from app.utilidades.decimales import CERO, MESES_ANIO, UNO, a_decimal, potencia
from app.utilidades.fechas import avanzar_periodos_comerciales


@dataclass
class ParametrosCronograma:
    """Parametros de entrada para construir un cronograma de pagos."""

    monto_financiado: Decimal
    tem: Decimal
    plazo_meses: int
    tipo_gracia: TipoGracia
    meses_gracia: int
    seguro_desgravamen_anual: Decimal
    seguro_vehicular_mensual: Decimal
    gps_mantenimiento_mensual: Decimal
    cuota_final: Decimal
    fecha_inicio: date


@dataclass
class FilaCronograma:
    """Detalle calculado de un periodo del cronograma (valores sin redondear)."""

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    saldo_inicial: Decimal
    interes: Decimal
    amortizacion: Decimal
    seguro_desgravamen: Decimal
    seguro_vehicular: Decimal
    gps_mantenimiento: Decimal
    cuota_ordinaria: Decimal
    cuota_final_extraordinaria: Decimal
    cuota_total: Decimal
    saldo_final: Decimal


@dataclass
class ResultadoCronograma:
    """Cronograma generado junto con los totales acumulados sin redondear."""

    filas: list[FilaCronograma] = field(default_factory=list)
    cuota_ordinaria: Decimal = CERO
    cuota_final: Decimal = CERO
    cuota_total_promedio: Decimal = CERO
    total_intereses: Decimal = CERO
    total_amortizado: Decimal = CERO
    total_seguros: Decimal = CERO
    total_gps_mantenimiento: Decimal = CERO
    monto_total_pagado: Decimal = CERO


def calcular_cuota_francesa(
    saldo_base: Decimal,
    tasa_periodica: Decimal,
    numero_periodos: int,
    valor_futuro: Decimal = CERO,
) -> Decimal:
    """Calcula la cuota ordinaria constante del metodo frances con cuota balon.

        cuota = (saldo_base - VF * (1 + i)^(-n)) * i / (1 - (1 + i)^(-n))

    donde VF es el valor futuro (cuota balon) que quedara como saldo al final.
    Con VF = 0 se obtiene la cuota frances clasica. Si la tasa periodica es cero,
    la cuota amortiza linealmente el saldo neto del valor balon.
    """

    saldo_base = a_decimal(saldo_base)
    tasa_periodica = a_decimal(tasa_periodica)
    valor_futuro = a_decimal(valor_futuro)
    n = numero_periodos

    if n <= 0:
        raise ValueError("El numero de periodos ordinarios debe ser mayor que cero.")

    if tasa_periodica == CERO:
        return (saldo_base - valor_futuro) / Decimal(n)

    factor = potencia(UNO + tasa_periodica, Decimal(-n))
    numerador = (saldo_base - valor_futuro * factor) * tasa_periodica
    denominador = UNO - factor
    return numerador / denominador


def generar_cronograma(parametros: ParametrosCronograma) -> ResultadoCronograma:
    """Construye el cronograma completo de pagos con gracia y cuota balon.

    Aplica primero los periodos de gracia (total o parcial) y luego calcula la
    cuota ordinaria sobre el saldo resultante, descontando el valor balon, de
    modo que el saldo termine en cero tras pagar la cuota balon en el ultimo
    periodo.
    """

    monto_financiado = a_decimal(parametros.monto_financiado)
    tem = a_decimal(parametros.tem)
    desgravamen_mensual = a_decimal(parametros.seguro_desgravamen_anual) / MESES_ANIO
    seguro_vehicular = a_decimal(parametros.seguro_vehicular_mensual)
    gps_mantenimiento = a_decimal(parametros.gps_mantenimiento_mensual)
    cuota_final = a_decimal(parametros.cuota_final)

    plazo = parametros.plazo_meses
    meses_gracia = parametros.meses_gracia if parametros.tipo_gracia != TipoGracia.NINGUNA else 0
    periodos_normales = plazo - meses_gracia

    if periodos_normales <= 0:
        raise ValueError(
            "El plazo debe ser mayor que la cantidad de meses de gracia."
        )

    resultado = ResultadoCronograma(cuota_final=cuota_final)
    saldo = monto_financiado

    # Tramo de gracia: capitaliza intereses (total) o cobra solo intereses (parcial).
    for indice in range(1, meses_gracia + 1):
        fecha = avanzar_periodos_comerciales(parametros.fecha_inicio, indice)
        interes = saldo * tem
        desgravamen = saldo * desgravamen_mensual

        if parametros.tipo_gracia == TipoGracia.TOTAL:
            cuota_ordinaria = CERO
            saldo_final = saldo + interes
            tipo_periodo = TipoPeriodo.GRACIA_TOTAL
        else:  # Gracia parcial: se pagan los intereses, no se amortiza capital.
            cuota_ordinaria = interes
            saldo_final = saldo
            tipo_periodo = TipoPeriodo.GRACIA_PARCIAL

        cuota_total = cuota_ordinaria + desgravamen + seguro_vehicular + gps_mantenimiento

        resultado.filas.append(
            FilaCronograma(
                numero_periodo=indice,
                fecha_pago=fecha,
                tipo_periodo=tipo_periodo,
                saldo_inicial=saldo,
                interes=interes,
                amortizacion=CERO,
                seguro_desgravamen=desgravamen,
                seguro_vehicular=seguro_vehicular,
                gps_mantenimiento=gps_mantenimiento,
                cuota_ordinaria=cuota_ordinaria,
                cuota_final_extraordinaria=CERO,
                cuota_total=cuota_total,
                saldo_final=saldo_final,
            )
        )

        resultado.total_intereses += interes
        resultado.total_seguros += desgravamen + seguro_vehicular
        resultado.total_gps_mantenimiento += gps_mantenimiento
        resultado.monto_total_pagado += cuota_total
        saldo = saldo_final

    if cuota_final >= saldo:
        raise ValueError(
            "La cuota balon debe ser menor que el saldo a financiar."
        )

    # Cuota ordinaria del tramo regular, descontando el valor balon.
    cuota_ordinaria = calcular_cuota_francesa(saldo, tem, periodos_normales, cuota_final)
    resultado.cuota_ordinaria = cuota_ordinaria

    suma_cuota_total_ordinaria = CERO

    for indice in range(1, periodos_normales + 1):
        numero_periodo = meses_gracia + indice
        fecha = avanzar_periodos_comerciales(parametros.fecha_inicio, numero_periodo)
        interes = saldo * tem
        desgravamen = saldo * desgravamen_mensual
        es_ultimo = indice == periodos_normales

        if es_ultimo:
            # En la ultima cuota se amortiza todo el saldo: la parte regular de la
            # cuota mas la cuota balon. Esto fuerza el saldo final a cero exacto.
            amortizacion_regular = cuota_ordinaria - interes
            balon = saldo - amortizacion_regular
            amortizacion = saldo
            cuota_final_extra = balon
            saldo_final = CERO
            tipo_periodo = TipoPeriodo.CUOTA_FINAL if cuota_final > CERO else TipoPeriodo.CUOTA_ORDINARIA
        else:
            amortizacion = cuota_ordinaria - interes
            cuota_final_extra = CERO
            saldo_final = saldo - amortizacion
            tipo_periodo = TipoPeriodo.CUOTA_ORDINARIA

        cuota_total = (
            cuota_ordinaria
            + cuota_final_extra
            + desgravamen
            + seguro_vehicular
            + gps_mantenimiento
        )

        resultado.filas.append(
            FilaCronograma(
                numero_periodo=numero_periodo,
                fecha_pago=fecha,
                tipo_periodo=tipo_periodo,
                saldo_inicial=saldo,
                interes=interes,
                amortizacion=amortizacion,
                seguro_desgravamen=desgravamen,
                seguro_vehicular=seguro_vehicular,
                gps_mantenimiento=gps_mantenimiento,
                cuota_ordinaria=cuota_ordinaria,
                cuota_final_extraordinaria=cuota_final_extra,
                cuota_total=cuota_total,
                saldo_final=saldo_final,
            )
        )

        resultado.total_intereses += interes
        resultado.total_amortizado += amortizacion
        resultado.total_seguros += desgravamen + seguro_vehicular
        resultado.total_gps_mantenimiento += gps_mantenimiento
        resultado.monto_total_pagado += cuota_total
        # El promedio mensual representa la cuota regular (con seguros y cargos),
        # SIN la cuota balon: esta se paga aparte al final y se informa por separado.
        suma_cuota_total_ordinaria += cuota_total - cuota_final_extra
        saldo = saldo_final

    resultado.cuota_total_promedio = suma_cuota_total_ordinaria / Decimal(periodos_normales)

    return resultado
