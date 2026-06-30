"""Arma el cronograma de pagos del credito vehicular.

Idea general (producto "Compra Inteligente"):
El monto del prestamo se paga de dos formas a la vez:
  1) Cuotas mensuales normales (interes + parte del capital + seguros + cargos).
  2) Un pago grande al final, el "cuoton" (un porcentaje del precio del auto),
     que se difiere y se paga de una sola vez justo despues de la ultima cuota.

Como una parte de la deuda (el cuoton) se deja para el final, lo que se reparte
en las cuotas mensuales es menor, por eso esas cuotas salen mas baratas. Para
saber cuanto reparte cada mes, calculamos cuanto "vale hoy" ese cuoton y se lo
restamos al prestamo: el resto (saldo_financiado) es lo unico que amortizan las
cuotas mensuales. El cuoton, mientras tanto, va acumulando su interes mes a mes
hasta que se paga completo al final.

Al inicio puede haber meses de gracia: "total" = ese mes no se paga nada y el
interes se suma a la deuda; "parcial" = ese mes solo se paga el interes.

Todo se calcula con numeros de alta precision (Decimal) y solo se redondea al
mostrar el resultado. Cada mes equivale a 30 dias (mes comercial).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoPeriodo
from app.utilidades.decimales import CERO, UNO, a_decimal, potencia
from app.utilidades.fechas import avanzar_periodos_comerciales


@dataclass
class ParametrosCronograma:
    """Parametros de entrada para construir un cronograma de pagos."""

    monto_prestamo: Decimal           # lo que se presta (precio - cuota inicial + costos financiados)
    cuota_final: Decimal              # el cuoton: el pago grande del final
    tem: Decimal                      # tasa de interes mensual
    numero_cuotas: int                # cuantas cuotas mensuales (el cuoton se paga una despues)
    meses_gracia_total: int           # meses al inicio sin pagar nada
    meses_gracia_parcial: int         # meses al inicio pagando solo el interes
    seguro_desgravamen_mensual: Decimal  # % mensual del seguro de desgravamen
    seguro_riesgo_periodico: Decimal     # monto del seguro de riesgo por cuota
    gps_periodico: Decimal               # monto del GPS por cuota
    portes_periodico: Decimal            # monto de portes por cuota
    gastos_adm_periodico: Decimal        # monto de gastos administrativos por cuota
    fecha_inicio: date


@dataclass
class FilaCronograma:
    """Detalle calculado de un periodo del cronograma (valores sin redondear).

    Los importes se expresan como magnitudes positivas; `flujo` es el egreso del
    deudor de ese periodo (negativo).
    """

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    # Tramo del cuoton (cuota final diferida).
    saldo_inicial_cuoton: Decimal
    interes_cuoton: Decimal
    amortizacion_cuoton: Decimal
    desgravamen_cuoton: Decimal
    saldo_final_cuoton: Decimal
    # Tramo de la cuota regular.
    saldo_inicial: Decimal
    interes: Decimal
    cuota: Decimal
    amortizacion: Decimal
    seguro_desgravamen: Decimal
    seguro_riesgo: Decimal
    gps: Decimal
    portes: Decimal
    gastos_adm: Decimal
    saldo_final: Decimal
    flujo: Decimal


@dataclass
class ResultadoCronograma:
    """Cronograma generado junto con los totales acumulados sin redondear."""

    filas: list[FilaCronograma] = field(default_factory=list)
    saldo_financiado: Decimal = CERO   # lo que pagan las cuotas (prestamo - valor de hoy del cuoton)
    vp_cuoton: Decimal = CERO          # cuanto vale hoy el cuoton
    cuota_ordinaria: Decimal = CERO    # la cuota mensual normal
    total_intereses: Decimal = CERO
    total_amortizado: Decimal = CERO
    total_seguro_desgravamen: Decimal = CERO
    total_seguro_riesgo: Decimal = CERO
    total_gps: Decimal = CERO
    total_portes: Decimal = CERO
    total_gastos_adm: Decimal = CERO
    monto_total_pagado: Decimal = CERO   # total que paga la persona (sin la cuota inicial)


def calcular_cuota_francesa(
    saldo_base: Decimal, tasa_periodica: Decimal, numero_periodos: int
) -> Decimal:
    """Cuota francesa constante que amortiza el saldo a cero en n periodos."""

    saldo_base = a_decimal(saldo_base)
    tasa_periodica = a_decimal(tasa_periodica)
    n = numero_periodos
    if n <= 0:
        raise ValueError("El numero de periodos ordinarios debe ser mayor que cero.")
    if tasa_periodica == CERO:
        return saldo_base / Decimal(n)
    factor = potencia(UNO + tasa_periodica, Decimal(n))
    return saldo_base * tasa_periodica * factor / (factor - UNO)


def generar_cronograma(parametros: ParametrosCronograma) -> ResultadoCronograma:
    """Construye el cronograma completo (N+1 periodos) del metodo Compra Inteligente."""

    prestamo = a_decimal(parametros.monto_prestamo)
    cuota_final = a_decimal(parametros.cuota_final)
    tem = a_decimal(parametros.tem)
    desgravamen = a_decimal(parametros.seguro_desgravamen_mensual)
    seguro_riesgo = a_decimal(parametros.seguro_riesgo_periodico)
    gps = a_decimal(parametros.gps_periodico)
    portes = a_decimal(parametros.portes_periodico)
    gastos_adm = a_decimal(parametros.gastos_adm_periodico)

    n = parametros.numero_cuotas
    meses_total = parametros.meses_gracia_total
    meses_parcial = parametros.meses_gracia_parcial

    if n <= 0:
        raise ValueError("El numero de cuotas debe ser mayor que cero.")
    if meses_total + meses_parcial >= n:
        raise ValueError("Los meses de gracia deben ser menores que el numero de cuotas.")

    # La cuota mensual carga el interes y el seguro de desgravamen juntos.
    tasa_con_desgravamen = tem + desgravamen

    # Cuanto "vale hoy" el cuoton (su valor presente): se trae al presente el pago
    # final usando la tasa mensual a lo largo de los N+1 periodos. Ese monto se le
    # resta al prestamo; lo que queda (saldo_financiado) es lo que pagan las cuotas.
    vp_cuoton = cuota_final / potencia(UNO + tasa_con_desgravamen, Decimal(n + 1))
    saldo_financiado = prestamo - vp_cuoton
    if saldo_financiado <= CERO:
        raise ValueError(
            "La cuota final es demasiado alta: no queda saldo para las cuotas mensuales."
        )

    resultado = ResultadoCronograma(
        saldo_financiado=saldo_financiado, vp_cuoton=vp_cuoton
    )

    saldo = saldo_financiado          # lo que falta pagar con cuotas mensuales
    saldo_cuoton = vp_cuoton          # lo que falta crecer el cuoton hasta el final

    # Recorremos mes por mes, desde la cuota 1 hasta el pago del cuoton (N+1).
    for nc in range(1, n + 2):
        fecha = avanzar_periodos_comerciales(parametros.fecha_inicio, nc)

        # --- El cuoton (el pago grande del final) ---
        # Cada mes el cuoton acumula su interes y desgravamen (crece sin pagarse).
        interes_cuoton = saldo_cuoton * tem
        desgravamen_cuoton = saldo_cuoton * desgravamen
        if nc == n + 1:
            # Mes final: se paga el cuoton completo (saldo acumulado + lo del mes).
            amortizacion_cuoton = saldo_cuoton + interes_cuoton + desgravamen_cuoton
            saldo_final_cuoton = CERO
        else:
            amortizacion_cuoton = CERO
            saldo_final_cuoton = saldo_cuoton + interes_cuoton + desgravamen_cuoton

        # --- La cuota mensual normal ---
        if nc > n:
            # En el mes del cuoton (N+1) ya no hay cuota mensual, solo el cuoton.
            saldo_inicial = CERO
            interes = cuota = amortizacion = seguro_desgravamen = CERO
            saldo_final = CERO
            tipo_periodo = TipoPeriodo.CUOTA_FINAL
        else:
            saldo_inicial = saldo
            interes = saldo * tem                 # interes del mes sobre lo que falta
            seguro_desgravamen = saldo * desgravamen
            if nc <= meses_total:
                # Gracia total: no se paga nada; el interes se suma a la deuda.
                cuota = amortizacion = CERO
                saldo_final = saldo + interes
                tipo_periodo = TipoPeriodo.GRACIA_TOTAL
            elif nc <= meses_total + meses_parcial:
                # Gracia parcial: solo se paga el interes; la deuda queda igual.
                cuota = interes
                amortizacion = CERO
                saldo_final = saldo
                tipo_periodo = TipoPeriodo.GRACIA_PARCIAL
            else:
                # Cuota normal: la misma cantidad cada mes (metodo frances). Se
                # recalcula con lo que falta para que el saldo llegue justo a cero.
                periodos_restantes = n - nc + 1
                cuota = calcular_cuota_francesa(
                    saldo, tasa_con_desgravamen, periodos_restantes
                )
                # Lo que no es interes ni seguro baja la deuda (amortizacion).
                amortizacion = cuota - interes - seguro_desgravamen
                saldo_final = saldo - amortizacion
                tipo_periodo = TipoPeriodo.CUOTA_ORDINARIA
                if resultado.cuota_ordinaria == CERO:
                    resultado.cuota_ordinaria = cuota

        # --- Lo que efectivamente paga la persona este mes (el "flujo") ---
        # Cuota + seguro de riesgo + GPS + portes + gastos administrativos.
        egreso = cuota + seguro_riesgo + gps + portes + gastos_adm
        if tipo_periodo in (TipoPeriodo.GRACIA_TOTAL, TipoPeriodo.GRACIA_PARCIAL):
            # En los meses de gracia el desgravamen no va dentro de la cuota:
            # se cobra aparte, asi que aqui lo sumamos.
            egreso += seguro_desgravamen
        if nc == n + 1:
            egreso += amortizacion_cuoton        # el mes final tambien paga el cuoton
        flujo = -egreso                          # negativo: es dinero que sale

        resultado.filas.append(
            FilaCronograma(
                numero_periodo=nc,
                fecha_pago=fecha,
                tipo_periodo=tipo_periodo,
                saldo_inicial_cuoton=saldo_cuoton,
                interes_cuoton=interes_cuoton,
                amortizacion_cuoton=amortizacion_cuoton,
                desgravamen_cuoton=desgravamen_cuoton,
                saldo_final_cuoton=saldo_final_cuoton,
                saldo_inicial=saldo_inicial,
                interes=interes,
                cuota=cuota,
                amortizacion=amortizacion,
                seguro_desgravamen=seguro_desgravamen,
                seguro_riesgo=seguro_riesgo,
                gps=gps,
                portes=portes,
                gastos_adm=gastos_adm,
                saldo_final=saldo_final,
                flujo=flujo,
            )
        )

        # --- Vamos sumando los totales para el resumen final ---
        if nc <= n:
            # El interes del mes es lo que queda de la cuota tras quitar capital y seguro.
            resultado.total_intereses += cuota - amortizacion - seguro_desgravamen
            resultado.total_amortizado += amortizacion
            resultado.total_seguro_desgravamen += seguro_desgravamen
        resultado.total_amortizado += amortizacion_cuoton
        resultado.total_seguro_riesgo += seguro_riesgo
        resultado.total_gps += gps
        resultado.total_portes += portes
        resultado.total_gastos_adm += gastos_adm
        resultado.monto_total_pagado += egreso

        saldo = saldo_final
        saldo_cuoton = saldo_final_cuoton

    return resultado
