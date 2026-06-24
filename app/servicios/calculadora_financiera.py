"""Calculo del cronograma de pagos (metodo frances con cuoton diferido al periodo N+1)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoPeriodo
from app.utilidades.decimales import CERO, UNO, a_decimal, potencia
from app.utilidades.fechas import avanzar_periodos_comerciales


@dataclass
class ParametrosCronograma:
    """Parametros de entrada para construir un cronograma de pagos."""

    monto_prestamo: Decimal           # Prestamo = PV - CI + costos financiados
    cuota_final: Decimal              # CF (cuoton) = pCF * PV
    tem: Decimal                      # tasa efectiva mensual
    numero_cuotas: int                # N (cuotas regulares); el cuoton cae en N+1
    meses_gracia_total: int           # periodos de gracia total al inicio
    meses_gracia_parcial: int         # periodos de gracia parcial a continuacion
    seguro_desgravamen_mensual: Decimal  # pSegDes (decimal mensual)
    seguro_riesgo_periodico: Decimal     # SegRiePer (monto por periodo)
    gps_periodico: Decimal               # GPSPer (monto por periodo)
    portes_periodico: Decimal            # PortesPer (monto por periodo)
    gastos_adm_periodico: Decimal        # GasAdmPer (monto por periodo)
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
    saldo_financiado: Decimal = CERO   # Saldo = Prestamo - VP(cuoton)
    vp_cuoton: Decimal = CERO          # SICF[1] = CF / (1 + TEM + pSegDes)^(N+1)
    cuota_ordinaria: Decimal = CERO    # cuota regular en estado estable (sin gracia)
    total_intereses: Decimal = CERO
    total_amortizado: Decimal = CERO
    total_seguro_desgravamen: Decimal = CERO
    total_seguro_riesgo: Decimal = CERO
    total_gps: Decimal = CERO
    total_portes: Decimal = CERO
    total_gastos_adm: Decimal = CERO
    monto_total_pagado: Decimal = CERO   # suma de los egresos del deudor (sin el periodo 0)


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

    # Tasa de descuento del cuoton y de la cuota regular: TEM mas el desgravamen.
    tasa_con_desgravamen = tem + desgravamen

    # Valor presente del cuoton (se descuenta N+1 periodos) y saldo regular.
    vp_cuoton = cuota_final / potencia(UNO + tasa_con_desgravamen, Decimal(n + 1))
    saldo_financiado = prestamo - vp_cuoton
    if saldo_financiado <= CERO:
        raise ValueError(
            "La cuota final es demasiado alta: no queda saldo para las cuotas mensuales."
        )

    resultado = ResultadoCronograma(
        saldo_financiado=saldo_financiado, vp_cuoton=vp_cuoton
    )

    saldo = saldo_financiado          # SI del tramo regular
    saldo_cuoton = vp_cuoton          # SICF del tramo del cuoton

    for nc in range(1, n + 2):        # periodos 1..N+1
        fecha = avanzar_periodos_comerciales(parametros.fecha_inicio, nc)

        # --- Tramo del cuoton ---
        interes_cuoton = saldo_cuoton * tem
        desgravamen_cuoton = saldo_cuoton * desgravamen
        if nc == n + 1:
            # Ultimo periodo: se cancela el cuoton completo (= cuota final).
            amortizacion_cuoton = saldo_cuoton + interes_cuoton + desgravamen_cuoton
            saldo_final_cuoton = CERO
        else:
            amortizacion_cuoton = CERO
            saldo_final_cuoton = saldo_cuoton + interes_cuoton + desgravamen_cuoton

        # --- Tramo de la cuota regular ---
        if nc > n:
            # Periodo N+1: solo se paga el cuoton (no hay cuota regular).
            saldo_inicial = CERO
            interes = cuota = amortizacion = seguro_desgravamen = CERO
            saldo_final = CERO
            tipo_periodo = TipoPeriodo.CUOTA_FINAL
        else:
            saldo_inicial = saldo
            interes = saldo * tem
            seguro_desgravamen = saldo * desgravamen
            if nc <= meses_total:
                # Gracia total: no se paga; el interes se capitaliza al saldo.
                cuota = amortizacion = CERO
                saldo_final = saldo + interes
                tipo_periodo = TipoPeriodo.GRACIA_TOTAL
            elif nc <= meses_total + meses_parcial:
                # Gracia parcial: se paga solo el interes; el saldo no varia.
                cuota = interes
                amortizacion = CERO
                saldo_final = saldo
                tipo_periodo = TipoPeriodo.GRACIA_PARCIAL
            else:
                # Cuota ordinaria francesa (recalculada cada periodo: autoajustable).
                periodos_restantes = n - nc + 1
                cuota = calcular_cuota_francesa(
                    saldo, tasa_con_desgravamen, periodos_restantes
                )
                amortizacion = cuota - interes - seguro_desgravamen
                saldo_final = saldo - amortizacion
                tipo_periodo = TipoPeriodo.CUOTA_ORDINARIA
                if resultado.cuota_ordinaria == CERO:
                    resultado.cuota_ordinaria = cuota

        # --- Costos periodicos (todos los periodos, incluido el N+1) ---
        # --- Flujo (egreso del deudor del periodo) ---
        egreso = cuota + seguro_riesgo + gps + portes + gastos_adm
        if tipo_periodo in (TipoPeriodo.GRACIA_TOTAL, TipoPeriodo.GRACIA_PARCIAL):
            # En gracia el desgravamen no va dentro de la cuota: se suma aparte.
            egreso += seguro_desgravamen
        if nc == n + 1:
            egreso += amortizacion_cuoton
        flujo = -egreso

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

        # --- Totales (replican las sumas del Excel) ---
        if nc <= n:
            # Interes del tramo regular = SUM(Cuota) - SUM(A) - SUM(SegDes).
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
