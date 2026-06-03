"""Servicio de apoyo para construir, calcular y persistir simulaciones.

Convierte las solicitudes del API en la entrada del nucleo de calculo, ejecuta
la simulacion y mapea el resultado a los modelos ORM aplicando el redondeo de
presentacion en el momento de persistir (que es un resultado final).
"""

from datetime import date
from decimal import Decimal

from app.esquemas.simulacion import SimulacionCalcularRequest
from app.modelos.cronograma import CronogramaPago
from app.modelos.enumeraciones import Moneda
from app.modelos.simulacion import Simulacion
from app.modelos.vehiculo import Vehiculo
from app.servicios.servicio_simulacion import (
    EntradaSimulacion,
    ResultadoSimulacion,
    calcular_simulacion,
    redondear_cronograma,
)
from app.utilidades.decimales import a_decimal, redondear_moneda, redondear_tasa


def _texto_limpio(valor: str | None) -> str | None:
    """Normaliza un texto opcional: recorta espacios y vacios a None."""

    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


def convertir_precio(
    precio,
    moneda_origen: Moneda,
    moneda_destino: Moneda,
    tipo_cambio,
) -> Decimal:
    """Convierte el precio del vehiculo a la moneda del credito.

    El tipo de cambio es la cotizacion del Dolar en Soles (1 USD = `tipo_cambio`
    PEN). Si las monedas coinciden, el precio no cambia.
    """

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
    """Construye la entrada del calculo a partir de la solicitud y el vehiculo.

    El precio se convierte a la moneda del credito (que puede diferir de la del
    vehiculo). Si se indica `precio_operacion`, este ya esta en la moneda del
    credito y se usa tal cual (al editar o recalcular se conserva el precio
    original de la propuesta para la trazabilidad).
    """

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
        porcentaje_cuota_inicial=solicitud.porcentaje_cuota_inicial,
        plazo_meses=solicitud.plazo_meses,
        tipo_tasa=solicitud.tipo_tasa,
        valor_tasa=solicitud.valor_tasa,
        capitalizacion=solicitud.capitalizacion,
        tipo_gracia=solicitud.tipo_gracia,
        meses_gracia=solicitud.meses_gracia,
        porcentaje_cuota_final=solicitud.porcentaje_cuota_final,
        seguro_desgravamen_anual=solicitud.seguro_desgravamen_anual,
        desgravamen_consentido=solicitud.desgravamen_consentido,
        seguro_vehicular_mensual=solicitud.seguro_vehicular_mensual,
        gps_instalacion=solicitud.gps_instalacion,
        gps_mantenimiento_mensual=solicitud.gps_mantenimiento_mensual,
        gps_reposicion=solicitud.gps_reposicion,
        gastos_notariales=solicitud.gastos_notariales,
        gastos_registrales=solicitud.gastos_registrales,
        tasacion=solicitud.tasacion,
        cok_anual=solicitud.cok_anual,
        tasa_descuento_van=solicitud.tasa_descuento_van,
        tasa_moratoria_anual=solicitud.tasa_moratoria_anual,
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

    simulacion.nombre = solicitud.nombre
    simulacion.moneda = resultado.moneda
    simulacion.tipo_cambio_referencial = (
        redondear_tasa(solicitud.tipo_cambio_referencial, 6)
        if solicitud.tipo_cambio_referencial is not None
        else None
    )
    simulacion.precio_vehiculo = redondear_moneda(resultado.precio_vehiculo)
    simulacion.cuota_inicial = redondear_moneda(resultado.cuota_inicial)
    simulacion.porcentaje_cuota_inicial = redondear_tasa(resultado.porcentaje_cuota_inicial)
    simulacion.monto_financiado = redondear_moneda(resultado.monto_financiado)
    simulacion.plazo_meses = resultado.plazo_meses
    simulacion.tipo_tasa = resultado.tipo_tasa
    simulacion.tasa_ingresada = redondear_tasa(resultado.tasa_ingresada)
    simulacion.capitalizacion = resultado.capitalizacion
    simulacion.tea_equivalente = redondear_tasa(resultado.tea_equivalente)
    simulacion.tem = redondear_tasa(resultado.tem)
    simulacion.tipo_gracia = resultado.tipo_gracia
    simulacion.meses_gracia = resultado.meses_gracia
    simulacion.fecha_inicio = solicitud.fecha_inicio or date.today()

    simulacion.porcentaje_cuota_final = redondear_tasa(solicitud.porcentaje_cuota_final)
    simulacion.cuota_final = redondear_moneda(resultado.cuota_final)
    simulacion.seguro_desgravamen_anual = redondear_tasa(solicitud.seguro_desgravamen_anual)
    simulacion.desgravamen_consentido = solicitud.desgravamen_consentido
    simulacion.seguro_vehicular_mensual = redondear_moneda(solicitud.seguro_vehicular_mensual)
    simulacion.gps_instalacion = redondear_moneda(solicitud.gps_instalacion)
    simulacion.gps_mantenimiento_mensual = redondear_moneda(solicitud.gps_mantenimiento_mensual)
    simulacion.gps_reposicion = redondear_moneda(solicitud.gps_reposicion)
    simulacion.gastos_notariales = redondear_moneda(solicitud.gastos_notariales)
    simulacion.gastos_registrales = redondear_moneda(solicitud.gastos_registrales)
    simulacion.tasacion = redondear_moneda(solicitud.tasacion)
    simulacion.gastos_iniciales = redondear_moneda(resultado.total_gastos_iniciales)
    simulacion.cok_anual = redondear_tasa(resultado.cok_anual)
    simulacion.tasa_descuento_van = redondear_tasa(resultado.tasa_descuento_van)
    simulacion.tasa_moratoria_anual = redondear_tasa(solicitud.tasa_moratoria_anual)
    simulacion.aseguradora = _texto_limpio(solicitud.aseguradora)
    simulacion.numero_poliza = _texto_limpio(solicitud.numero_poliza)
    simulacion.coberturas = _texto_limpio(solicitud.coberturas)

    simulacion.cuota_mensual = redondear_moneda(resultado.cuota_mensual)
    simulacion.cuota_total_promedio = redondear_moneda(resultado.cuota_total_promedio)
    simulacion.van = redondear_moneda(resultado.van)
    simulacion.tir_mensual = (
        redondear_tasa(resultado.tir_mensual) if resultado.tir_mensual is not None else None
    )
    simulacion.tir_anual = (
        redondear_tasa(resultado.tir_anual) if resultado.tir_anual is not None else None
    )
    simulacion.tcea = redondear_tasa(resultado.tcea) if resultado.tcea is not None else None
    simulacion.costo_total_credito = redondear_moneda(resultado.costo_total_credito)
    simulacion.total_intereses = redondear_moneda(resultado.total_intereses)
    simulacion.total_amortizado = redondear_moneda(resultado.total_amortizado)
    simulacion.total_seguros = redondear_moneda(resultado.total_seguros)
    simulacion.total_cargos_desembolso = redondear_moneda(resultado.total_cargos_desembolso)
    simulacion.total_gps_mantenimiento = redondear_moneda(resultado.total_gps_mantenimiento)
    simulacion.monto_total_pagado = redondear_moneda(resultado.monto_total_pagado)


def construir_filas_cronograma(
    resultado: ResultadoSimulacion,
) -> list[CronogramaPago]:
    """Crea las filas ORM del cronograma usando el redondeo reconciliado."""

    filas: list[CronogramaPago] = []
    for fila in redondear_cronograma(resultado):
        filas.append(
            CronogramaPago(
                numero_periodo=fila["numero_periodo"],
                fecha_pago=fila["fecha_pago"],
                tipo_periodo=fila["tipo_periodo"],
                saldo_inicial=fila["saldo_inicial"],
                interes=fila["interes"],
                amortizacion=fila["amortizacion"],
                seguro_desgravamen=fila["seguro_desgravamen"],
                seguro_vehicular=fila["seguro_vehicular"],
                gps_mantenimiento=fila["gps_mantenimiento"],
                cuota_ordinaria=fila["cuota_ordinaria"],
                cuota_final_extraordinaria=fila["cuota_final_extraordinaria"],
                cuota_total=fila["cuota_total"],
                saldo_final=fila["saldo_final"],
            )
        )
    return filas
