"""Orquestador del calculo completo de una simulacion de credito vehicular.

Combina la conversion de tasas, la generacion del cronograma (metodo frances con
cuota balon de Compra Inteligente) y el calculo de los indicadores de
transparencia (VAN, TIR y TCEA) en una unica operacion. El resultado conserva
los valores en `Decimal` de alta precision; el redondeo de presentacion se
realiza con `redondear_resultado`.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import (
    Capitalizacion,
    Moneda,
    TipoGracia,
    TipoTasa,
)
from app.servicios import servicio_tasas, servicio_van_tir
from app.servicios.calculadora_financiera import (
    FilaCronograma,
    ParametrosCronograma,
    generar_cronograma,
)
from app.servicios.servicio_tcea import calcular_tcea
from app.utilidades.decimales import (
    CERO,
    MESES_ANIO,
    UNO,
    a_decimal,
    potencia,
    redondear_moneda,
    redondear_tasa,
)


@dataclass
class EntradaSimulacion:
    """Parametros de entrada validados para calcular una simulacion."""

    moneda: Moneda
    precio_vehiculo: Decimal
    porcentaje_cuota_inicial: Decimal
    plazo_meses: int
    tipo_tasa: TipoTasa
    valor_tasa: Decimal
    capitalizacion: Capitalizacion | None
    tipo_gracia: TipoGracia
    meses_gracia: int
    # Cuota balon: porcentaje del precio del vehiculo que queda como pago final.
    porcentaje_cuota_final: Decimal = CERO
    # Seguro de desgravamen: solo se cobra si el cliente lo contrato (consentimiento).
    seguro_desgravamen_anual: Decimal = CERO
    desgravamen_consentido: bool = False
    # Seguro vehicular mensual (en la cuota).
    seguro_vehicular_mensual: Decimal = CERO
    # GPS: instalacion (cargo unico al desembolso) y mantenimiento (mensual, en la
    # cuota); la reposicion es un tarifario referencial que NO se cobra al
    # contratar ni entra en la TCEA. Todos forman parte de la oferta del credito.
    gps_instalacion: Decimal = CERO
    gps_mantenimiento_mensual: Decimal = CERO
    gps_reposicion: Decimal = CERO
    # Gastos de terceros que se financian (se suman al monto y entran en la TCEA).
    gastos_notariales: Decimal = CERO
    gastos_registrales: Decimal = CERO
    tasacion: Decimal = CERO
    cok_anual: Decimal = CERO
    tasa_descuento_van: Decimal | None = None
    # Tasa moratoria nominal anual (no capitalizable): informativa para la hoja resumen.
    tasa_moratoria_anual: Decimal = CERO
    tipo_cambio_referencial: Decimal | None = None
    fecha_inicio: date = field(default_factory=date.today)


@dataclass
class ResultadoSimulacion:
    """Indicadores calculados y cronograma de la simulacion (sin redondear)."""

    moneda: Moneda
    precio_vehiculo: Decimal
    cuota_inicial: Decimal
    porcentaje_cuota_inicial: Decimal
    cuota_final: Decimal
    monto_financiado: Decimal
    plazo_meses: int
    tipo_tasa: TipoTasa
    tasa_ingresada: Decimal
    capitalizacion: Capitalizacion | None
    tea_equivalente: Decimal
    tem: Decimal
    tipo_gracia: TipoGracia
    meses_gracia: int
    cuota_mensual: Decimal
    cuota_total_promedio: Decimal
    total_intereses: Decimal
    total_amortizado: Decimal
    total_seguros: Decimal
    # Gastos de terceros financiados (incluidos en el monto financiado).
    total_gastos_iniciales: Decimal
    # Cargo unico cobrado al desembolso (instalacion de GPS; afecta la TCEA).
    total_cargos_desembolso: Decimal
    # Mantenimiento de GPS cobrado dentro de las cuotas (afecta la TCEA).
    total_gps_mantenimiento: Decimal
    costo_total_credito: Decimal
    monto_total_pagado: Decimal
    cok_anual: Decimal
    cok_mensual: Decimal
    tasa_descuento_van: Decimal
    van: Decimal
    tir_mensual: Decimal | None
    tir_anual: Decimal | None
    tcea: Decimal | None
    filas: list[FilaCronograma]


def _validar_entrada(entrada: EntradaSimulacion) -> None:
    """Valida las reglas de negocio numericas antes de calcular.

    Lanza `ValueError` con un mensaje en espanol ante cualquier violacion; las
    rutas traducen estas excepciones a respuestas HTTP 400.
    """

    if entrada.precio_vehiculo <= CERO:
        raise ValueError("El precio del vehiculo debe ser mayor que cero.")
    if not (CERO <= entrada.porcentaje_cuota_inicial <= UNO):
        raise ValueError("El porcentaje de cuota inicial debe estar entre 0% y 100%.")
    if not (CERO <= entrada.porcentaje_cuota_final < UNO):
        raise ValueError("El porcentaje de cuota balon debe estar entre 0% y 100%.")
    if entrada.plazo_meses <= 0:
        raise ValueError("El plazo en meses debe ser mayor que cero.")
    if entrada.valor_tasa < CERO:
        raise ValueError("La tasa de interes no puede ser negativa.")
    if entrada.tipo_tasa == TipoTasa.NOMINAL and entrada.capitalizacion is None:
        raise ValueError(
            "La capitalizacion es obligatoria cuando la tasa es nominal."
        )

    meses_gracia = (
        entrada.meses_gracia if entrada.tipo_gracia != TipoGracia.NINGUNA else 0
    )
    if meses_gracia < 0:
        raise ValueError("Los meses de gracia no pueden ser negativos.")
    if meses_gracia >= entrada.plazo_meses:
        raise ValueError(
            "Los meses de gracia deben ser menores que el plazo total."
        )

    for nombre, valor in (
        ("seguro de desgravamen", entrada.seguro_desgravamen_anual),
        ("seguro vehicular", entrada.seguro_vehicular_mensual),
        ("instalacion de GPS", entrada.gps_instalacion),
        ("mantenimiento de GPS", entrada.gps_mantenimiento_mensual),
        ("reposicion de GPS", entrada.gps_reposicion),
        ("gastos notariales", entrada.gastos_notariales),
        ("gastos registrales", entrada.gastos_registrales),
        ("tasacion", entrada.tasacion),
        ("tasa moratoria", entrada.tasa_moratoria_anual),
    ):
        if valor < CERO:
            raise ValueError(f"El valor de {nombre} no puede ser negativo.")


def calcular_simulacion(entrada: EntradaSimulacion) -> ResultadoSimulacion:
    """Calcula los montos derivados, el cronograma y los indicadores financieros."""

    _validar_entrada(entrada)

    precio = a_decimal(entrada.precio_vehiculo)
    porcentaje_inicial = a_decimal(entrada.porcentaje_cuota_inicial)

    # Gastos de terceros (notariales, registrales, tasacion): se financian, es
    # decir, se suman al monto a financiar y se pagan dentro de las cuotas. Al ser
    # condicion de la oferta, entran en la TCEA.
    gastos_financiados = (
        a_decimal(entrada.gastos_notariales)
        + a_decimal(entrada.gastos_registrales)
        + a_decimal(entrada.tasacion)
    )

    # El desgravamen solo se cobra si el cliente dio su consentimiento expreso.
    desgravamen_anual = (
        a_decimal(entrada.seguro_desgravamen_anual)
        if entrada.desgravamen_consentido
        else CERO
    )
    seguro_vehicular_cuota = a_decimal(entrada.seguro_vehicular_mensual)

    # GPS: la instalacion es un cargo unico que se cobra al desembolso y el
    # mantenimiento se cobra dentro de cada cuota (ambos en la TCEA). La REPOSICION
    # es un tarifario referencial de un evento futuro: NO se cobra al contratar ni
    # entra en la TCEA (solo se informa).
    gps_instalacion = a_decimal(entrada.gps_instalacion)
    gps_mantenimiento = a_decimal(entrada.gps_mantenimiento_mensual)

    cuota_inicial = precio * porcentaje_inicial
    monto_financiado = precio - cuota_inicial + gastos_financiados

    if monto_financiado <= CERO:
        raise ValueError(
            "El monto financiado debe ser mayor que cero; revise la cuota inicial."
        )

    # Cuota balon (valor futuro): porcentaje del precio del vehiculo.
    cuota_final = precio * a_decimal(entrada.porcentaje_cuota_final)
    if cuota_final >= monto_financiado:
        raise ValueError(
            "La cuota balon debe ser menor que el monto a financiar; "
            "reduzca el porcentaje de cuota balon o la cuota inicial."
        )

    # Conversion de la tasa ingresada a TEA y TEM equivalentes.
    tea, tem = servicio_tasas.calcular_tasas_equivalentes(
        entrada.tipo_tasa, entrada.valor_tasa, entrada.capitalizacion
    )

    meses_gracia = (
        entrada.meses_gracia if entrada.tipo_gracia != TipoGracia.NINGUNA else 0
    )

    parametros = ParametrosCronograma(
        monto_financiado=monto_financiado,
        tem=tem,
        plazo_meses=entrada.plazo_meses,
        tipo_gracia=entrada.tipo_gracia,
        meses_gracia=meses_gracia,
        seguro_desgravamen_anual=desgravamen_anual,
        seguro_vehicular_mensual=seguro_vehicular_cuota,
        gps_mantenimiento_mensual=gps_mantenimiento,
        cuota_final=cuota_final,
        fecha_inicio=entrada.fecha_inicio,
    )
    cronograma = generar_cronograma(parametros)

    # Unico cargo cobrado al desembolso (reduce el desembolso neto y eleva la
    # TCEA): la instalacion del GPS.
    cargos_unicos = gps_instalacion
    costo_total_credito = cronograma.monto_total_pagado + cargos_unicos
    monto_total_pagado = costo_total_credito + cuota_inicial

    # Flujo del deudor para VAN/TIR/TCEA (norma SBS de transparencia): en el
    # periodo 0 el cliente recibe el valor del vehiculo financiado
    # (precio - cuota inicial) MENOS la instalacion del GPS cobrada al desembolso.
    # Los gastos financiados NO son dinero recibido: se trasladan a terceros y
    # solo elevan las cuotas, por lo que aumentan la TCEA.
    cok_mensual = servicio_tasas.anual_a_mensual_compuesta(a_decimal(entrada.cok_anual))
    desembolso_neto = precio - cuota_inicial - cargos_unicos
    if desembolso_neto <= CERO:
        raise ValueError(
            "El desembolso neto al cliente debe ser mayor que cero; "
            "revise la cuota inicial y la instalacion del GPS."
        )
    flujos_deudor: list[Decimal] = [desembolso_neto]
    flujos_deudor.extend(-fila.cuota_total for fila in cronograma.filas)

    # El VAN se descuenta con la tasa de descuento del VAN; si no se indica
    # (None) se usa el COK. Un 0 explicito se respeta (VAN sin descuento).
    tasa_van_anual = (
        a_decimal(entrada.tasa_descuento_van)
        if entrada.tasa_descuento_van is not None
        else a_decimal(entrada.cok_anual)
    )
    tasa_van_mensual = servicio_tasas.anual_a_mensual_compuesta(tasa_van_anual)
    van = servicio_van_tir.calcular_van(flujos_deudor, tasa_van_mensual)

    tir_mensual = servicio_van_tir.calcular_tir(flujos_deudor)
    tir_anual = (
        potencia(UNO + tir_mensual, MESES_ANIO) - UNO if tir_mensual is not None else None
    )

    _, tcea = calcular_tcea(flujos_deudor)

    return ResultadoSimulacion(
        moneda=entrada.moneda,
        precio_vehiculo=precio,
        cuota_inicial=cuota_inicial,
        porcentaje_cuota_inicial=porcentaje_inicial,
        cuota_final=cuota_final,
        monto_financiado=monto_financiado,
        plazo_meses=entrada.plazo_meses,
        tipo_tasa=entrada.tipo_tasa,
        tasa_ingresada=a_decimal(entrada.valor_tasa),
        capitalizacion=entrada.capitalizacion,
        tea_equivalente=tea,
        tem=tem,
        tipo_gracia=entrada.tipo_gracia,
        meses_gracia=meses_gracia,
        cuota_mensual=cronograma.cuota_ordinaria,
        cuota_total_promedio=cronograma.cuota_total_promedio,
        total_intereses=cronograma.total_intereses,
        total_amortizado=cronograma.total_amortizado,
        total_seguros=cronograma.total_seguros,
        total_gastos_iniciales=gastos_financiados,
        total_cargos_desembolso=cargos_unicos,
        total_gps_mantenimiento=cronograma.total_gps_mantenimiento,
        costo_total_credito=costo_total_credito,
        monto_total_pagado=monto_total_pagado,
        cok_anual=a_decimal(entrada.cok_anual),
        cok_mensual=cok_mensual,
        tasa_descuento_van=tasa_van_anual,
        van=van,
        tir_mensual=tir_mensual,
        tir_anual=tir_anual,
        tcea=tcea,
        filas=cronograma.filas,
    )


def redondear_fila(fila: FilaCronograma) -> dict:
    """Convierte una fila del cronograma a un diccionario con redondeo de presentacion."""

    return {
        "numero_periodo": fila.numero_periodo,
        "fecha_pago": fila.fecha_pago,
        "tipo_periodo": fila.tipo_periodo,
        "saldo_inicial": redondear_moneda(fila.saldo_inicial),
        "interes": redondear_moneda(fila.interes),
        "amortizacion": redondear_moneda(fila.amortizacion),
        "seguro_desgravamen": redondear_moneda(fila.seguro_desgravamen),
        "seguro_vehicular": redondear_moneda(fila.seguro_vehicular),
        "gps_mantenimiento": redondear_moneda(fila.gps_mantenimiento),
        "cuota_ordinaria": redondear_moneda(fila.cuota_ordinaria),
        "cuota_final_extraordinaria": redondear_moneda(fila.cuota_final_extraordinaria),
        "cuota_total": redondear_moneda(fila.cuota_total),
        "saldo_final": redondear_moneda(fila.saldo_final),
    }


def redondear_cronograma(resultado: ResultadoSimulacion) -> list[dict]:
    """Redondea el cronograma a presentacion y reconcilia el redondeo en la ultima fila.

    El redondeo independiente de cada fila puede hacer que la suma de las
    amortizaciones mostradas difiera por centimos del capital realmente
    amortizado (que NO es el monto financiado cuando hubo gracia total: ahi se
    capitalizan intereses). Para que el cronograma cuadre y el saldo cierre en
    cero, la ultima fila absorbe esa diferencia en su parte regular, mientras que
    la cuota balon se muestra con su valor contractual exacto (sin centimos de
    arrastre ni valores negativos).
    """

    filas = [redondear_fila(fila) for fila in resultado.filas]
    if not filas:
        return filas

    # El capital amortizado real es la suma exacta de amortizaciones (incluye los
    # intereses capitalizados durante la gracia total).
    amortizado_real = redondear_moneda(
        sum(fila.amortizacion for fila in resultado.filas)
    )
    suma_redondeada = sum(fila["amortizacion"] for fila in filas)
    diferencia = amortizado_real - suma_redondeada

    ultima = filas[-1]
    ultima["amortizacion"] = ultima["amortizacion"] + diferencia
    ultima["saldo_final"] = redondear_moneda(CERO)
    # La cuota balon mantiene su valor contractual (porcentaje del precio); la
    # parte regular de la ultima cuota es el resto de la amortizacion.
    ultima["cuota_final_extraordinaria"] = redondear_moneda(resultado.cuota_final)
    parte_regular = ultima["amortizacion"] - ultima["cuota_final_extraordinaria"]
    ultima["cuota_ordinaria"] = ultima["interes"] + parte_regular
    ultima["cuota_total"] = (
        ultima["cuota_ordinaria"]
        + ultima["cuota_final_extraordinaria"]
        + ultima["seguro_desgravamen"]
        + ultima["seguro_vehicular"]
        + ultima["gps_mantenimiento"]
    )
    return filas


def redondear_resultado(resultado: ResultadoSimulacion) -> dict:
    """Convierte el resultado completo a un diccionario con redondeo de presentacion.

    Los importes monetarios se redondean a dos decimales y las tasas a siete
    decimales. Esta es la unica etapa donde se aplica redondeo.
    """

    return {
        "moneda": resultado.moneda,
        "precio_vehiculo": redondear_moneda(resultado.precio_vehiculo),
        "cuota_inicial": redondear_moneda(resultado.cuota_inicial),
        "porcentaje_cuota_inicial": redondear_tasa(resultado.porcentaje_cuota_inicial),
        "cuota_final": redondear_moneda(resultado.cuota_final),
        "monto_financiado": redondear_moneda(resultado.monto_financiado),
        "plazo_meses": resultado.plazo_meses,
        "tipo_tasa": resultado.tipo_tasa,
        "tasa_ingresada": redondear_tasa(resultado.tasa_ingresada),
        "capitalizacion": resultado.capitalizacion,
        "tea_equivalente": redondear_tasa(resultado.tea_equivalente),
        "tem": redondear_tasa(resultado.tem),
        "tipo_gracia": resultado.tipo_gracia,
        "meses_gracia": resultado.meses_gracia,
        "cuota_mensual": redondear_moneda(resultado.cuota_mensual),
        "cuota_total_promedio": redondear_moneda(resultado.cuota_total_promedio),
        "total_intereses": redondear_moneda(resultado.total_intereses),
        "total_amortizado": redondear_moneda(resultado.total_amortizado),
        "total_seguros": redondear_moneda(resultado.total_seguros),
        "total_gastos_iniciales": redondear_moneda(resultado.total_gastos_iniciales),
        "total_cargos_desembolso": redondear_moneda(resultado.total_cargos_desembolso),
        "total_gps_mantenimiento": redondear_moneda(resultado.total_gps_mantenimiento),
        "costo_total_credito": redondear_moneda(resultado.costo_total_credito),
        "monto_total_pagado": redondear_moneda(resultado.monto_total_pagado),
        "cok_anual": redondear_tasa(resultado.cok_anual),
        "cok_mensual": redondear_tasa(resultado.cok_mensual),
        "tasa_descuento_van": redondear_tasa(resultado.tasa_descuento_van),
        "van": redondear_moneda(resultado.van),
        "tir_mensual": (
            redondear_tasa(resultado.tir_mensual) if resultado.tir_mensual is not None else None
        ),
        "tir_anual": (
            redondear_tasa(resultado.tir_anual) if resultado.tir_anual is not None else None
        ),
        "tcea": redondear_tasa(resultado.tcea) if resultado.tcea is not None else None,
        "cronograma": redondear_cronograma(resultado),
    }
