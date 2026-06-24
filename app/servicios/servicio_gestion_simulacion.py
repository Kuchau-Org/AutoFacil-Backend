"""Construye, calcula y persiste simulaciones (mapeo entre request y modelo)."""

from datetime import date
from decimal import Decimal

from app.esquemas.simulacion import SimulacionCalcularRequest
from app.modelos.cronograma import CronogramaPago
from app.modelos.enumeraciones import Moneda
from app.modelos.simulacion import Simulacion
from app.modelos.vehiculo import Vehiculo
from app.servicios.servicio_simulacion import (
    CostoInicial,
    EntradaSimulacion,
    ResultadoSimulacion,
    calcular_simulacion,
    redondear_cronograma,
)
from app.utilidades.decimales import a_decimal, redondear_moneda, redondear_tasa


def convertir_precio(precio, moneda_origen: Moneda, moneda_destino: Moneda, tipo_cambio) -> Decimal:
    """Convierte el precio del vehiculo a la moneda del credito (1 USD = tipo_cambio PEN)."""

    precio = a_decimal(precio)
    if moneda_origen == moneda_destino:
        return precio
    if tipo_cambio is None or a_decimal(tipo_cambio) <= 0:
        raise ValueError(
            "Se requiere un tipo de cambio valido para simular en una moneda "
            "distinta a la del vehiculo."
        )
    tipo_cambio = a_decimal(tipo_cambio)
    if moneda_origen == Moneda.SOLES and moneda_destino == Moneda.DOLARES:
        return precio / tipo_cambio
    # De Dolares a Soles.
    return precio * tipo_cambio


def construir_entrada(
    solicitud: SimulacionCalcularRequest,
    vehiculo: Vehiculo,
    precio_operacion: object = None,
) -> EntradaSimulacion:
    """Construye la entrada del calculo a partir de la solicitud y el vehiculo."""

    if precio_operacion is not None:
        precio = a_decimal(precio_operacion)
    else:
        precio = convertir_precio(
            vehiculo.precio,
            vehiculo.moneda,
            solicitud.moneda,
            solicitud.tipo_cambio_referencial,
        )
    return EntradaSimulacion(
        moneda=solicitud.moneda,
        precio_vehiculo=precio,
        plan=solicitud.plan,
        porcentaje_cuota_inicial=solicitud.porcentaje_cuota_inicial,
        tipo_tasa=solicitud.tipo_tasa,
        valor_tasa=solicitud.valor_tasa,
        capitalizacion=solicitud.capitalizacion,
        meses_gracia_total=solicitud.meses_gracia_total,
        meses_gracia_parcial=solicitud.meses_gracia_parcial,
        costo_notarial=CostoInicial(
            a_decimal(solicitud.costo_notarial), solicitud.costo_notarial_financiado
        ),
        costo_registral=CostoInicial(
            a_decimal(solicitud.costo_registral), solicitud.costo_registral_financiado
        ),
        costo_tasacion=CostoInicial(
            a_decimal(solicitud.costo_tasacion), solicitud.costo_tasacion_financiado
        ),
        comision_estudio=CostoInicial(
            a_decimal(solicitud.comision_estudio), solicitud.comision_estudio_financiado
        ),
        comision_activacion=CostoInicial(
            a_decimal(solicitud.comision_activacion), solicitud.comision_activacion_financiado
        ),
        gps_periodico=solicitud.gps_periodico,
        portes_periodico=solicitud.portes_periodico,
        gastos_adm_periodico=solicitud.gastos_adm_periodico,
        seguro_desgravamen_mensual=solicitud.seguro_desgravamen_mensual,
        seguro_riesgo_anual=solicitud.seguro_riesgo_anual,
        cok_anual=solicitud.cok_anual,
        tipo_cambio_referencial=solicitud.tipo_cambio_referencial,
        fecha_inicio=solicitud.fecha_inicio or date.today(),
    )


def calcular_desde_solicitud(
    solicitud: SimulacionCalcularRequest,
    vehiculo: Vehiculo,
    precio_operacion: object = None,
) -> ResultadoSimulacion:
    """Ejecuta el calculo financiero completo a partir de la solicitud."""

    entrada = construir_entrada(solicitud, vehiculo, precio_operacion)
    return calcular_simulacion(entrada)


def aplicar_resultado_a_modelo(
    simulacion: Simulacion,
    solicitud: SimulacionCalcularRequest,
    resultado: ResultadoSimulacion,
) -> None:
    """Vuelca los parametros y resultados (redondeados) sobre el modelo ORM."""

    simulacion.nombre = (solicitud.nombre or "").strip() or None
    simulacion.moneda = resultado.moneda
    simulacion.tipo_cambio_referencial = (
        redondear_tasa(solicitud.tipo_cambio_referencial, 6)
        if solicitud.tipo_cambio_referencial is not None
        else None
    )
    simulacion.fecha_inicio = solicitud.fecha_inicio or date.today()

    # --- Parametros de entrada ---
    simulacion.precio_vehiculo = redondear_moneda(resultado.precio_vehiculo)
    simulacion.plan = resultado.plan
    simulacion.porcentaje_cuota_inicial = redondear_tasa(resultado.porcentaje_cuota_inicial)
    simulacion.tipo_tasa = resultado.tipo_tasa
    simulacion.tasa_ingresada = redondear_tasa(resultado.tasa_ingresada)
    simulacion.capitalizacion = resultado.capitalizacion
    simulacion.meses_gracia_total = resultado.meses_gracia_total
    simulacion.meses_gracia_parcial = resultado.meses_gracia_parcial
    simulacion.costo_notarial = redondear_moneda(solicitud.costo_notarial)
    simulacion.costo_notarial_financiado = solicitud.costo_notarial_financiado
    simulacion.costo_registral = redondear_moneda(solicitud.costo_registral)
    simulacion.costo_registral_financiado = solicitud.costo_registral_financiado
    simulacion.costo_tasacion = redondear_moneda(solicitud.costo_tasacion)
    simulacion.costo_tasacion_financiado = solicitud.costo_tasacion_financiado
    simulacion.comision_estudio = redondear_moneda(solicitud.comision_estudio)
    simulacion.comision_estudio_financiado = solicitud.comision_estudio_financiado
    simulacion.comision_activacion = redondear_moneda(solicitud.comision_activacion)
    simulacion.comision_activacion_financiado = solicitud.comision_activacion_financiado
    simulacion.gps_periodico = redondear_moneda(solicitud.gps_periodico)
    simulacion.portes_periodico = redondear_moneda(solicitud.portes_periodico)
    simulacion.gastos_adm_periodico = redondear_moneda(solicitud.gastos_adm_periodico)
    simulacion.seguro_desgravamen_mensual = redondear_tasa(solicitud.seguro_desgravamen_mensual)
    simulacion.seguro_riesgo_anual = redondear_tasa(solicitud.seguro_riesgo_anual)
    simulacion.cok_anual = redondear_tasa(resultado.cok_anual)

    # --- Resultados derivados ---
    simulacion.numero_cuotas = resultado.numero_cuotas
    simulacion.numero_anios = resultado.numero_anios
    simulacion.porcentaje_cuota_final = redondear_tasa(resultado.porcentaje_cuota_final)
    simulacion.cuota_inicial = redondear_moneda(resultado.cuota_inicial)
    simulacion.cuota_final = redondear_moneda(resultado.cuota_final)
    simulacion.monto_prestamo = redondear_moneda(resultado.monto_prestamo)
    simulacion.saldo_financiado = redondear_moneda(resultado.saldo_financiado)
    simulacion.tea_equivalente = redondear_tasa(resultado.tea_equivalente)
    simulacion.tem = redondear_tasa(resultado.tem)
    simulacion.seguro_riesgo_periodico = redondear_moneda(resultado.seguro_riesgo_periodico)
    simulacion.total_costos_financiados = redondear_moneda(resultado.total_costos_financiados)
    simulacion.total_costos_efectivo = redondear_moneda(resultado.total_costos_efectivo)
    simulacion.cuota_mensual = redondear_moneda(resultado.cuota_mensual)
    simulacion.cok_mensual = redondear_tasa(resultado.cok_mensual)
    simulacion.van = redondear_moneda(resultado.van)
    simulacion.tir_mensual = (
        redondear_tasa(resultado.tir_mensual) if resultado.tir_mensual is not None else None
    )
    simulacion.tir_anual = (
        redondear_tasa(resultado.tir_anual) if resultado.tir_anual is not None else None
    )
    simulacion.tcea = redondear_tasa(resultado.tcea) if resultado.tcea is not None else None
    simulacion.total_intereses = redondear_moneda(resultado.total_intereses)
    simulacion.total_amortizado = redondear_moneda(resultado.total_amortizado)
    simulacion.total_seguro_desgravamen = redondear_moneda(resultado.total_seguro_desgravamen)
    simulacion.total_seguro_riesgo = redondear_moneda(resultado.total_seguro_riesgo)
    simulacion.total_gps = redondear_moneda(resultado.total_gps)
    simulacion.total_portes = redondear_moneda(resultado.total_portes)
    simulacion.total_gastos_adm = redondear_moneda(resultado.total_gastos_adm)
    simulacion.monto_total_pagado = redondear_moneda(resultado.monto_total_pagado)


def construir_filas_cronograma(resultado: ResultadoSimulacion) -> list[CronogramaPago]:
    """Crea las filas ORM del cronograma con el redondeo de presentacion."""

    return [
        CronogramaPago(
            numero_periodo=fila["numero_periodo"],
            fecha_pago=fila["fecha_pago"],
            tipo_periodo=fila["tipo_periodo"],
            saldo_inicial_cuoton=fila["saldo_inicial_cuoton"],
            interes_cuoton=fila["interes_cuoton"],
            amortizacion_cuoton=fila["amortizacion_cuoton"],
            desgravamen_cuoton=fila["desgravamen_cuoton"],
            saldo_final_cuoton=fila["saldo_final_cuoton"],
            saldo_inicial=fila["saldo_inicial"],
            interes=fila["interes"],
            cuota=fila["cuota"],
            amortizacion=fila["amortizacion"],
            seguro_desgravamen=fila["seguro_desgravamen"],
            seguro_riesgo=fila["seguro_riesgo"],
            gps=fila["gps"],
            portes=fila["portes"],
            gastos_adm=fila["gastos_adm"],
            saldo_final=fila["saldo_final"],
            flujo=fila["flujo"],
        )
        for fila in redondear_cronograma(resultado)
    ]
