"""Orquesta el calculo completo de una simulacion: tasas, cronograma e indicadores."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import Capitalizacion, Moneda, Plan, TipoTasa
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
class CostoInicial:
    """Costo o gasto inicial con su modalidad de pago (financiado o al contado)."""

    monto: Decimal = CERO
    # True = se financia (entra al prestamo); False = se paga al contado (efectivo).
    financiado: bool = True


@dataclass
class EntradaSimulacion:
    """Parametros de entrada validados para calcular una simulacion."""

    moneda: Moneda
    precio_vehiculo: Decimal
    plan: Plan
    porcentaje_cuota_inicial: Decimal
    tipo_tasa: TipoTasa
    valor_tasa: Decimal
    capitalizacion: Capitalizacion | None
    # Gracia al inicio: meses de gracia total y, a continuacion, de gracia parcial.
    meses_gracia_total: int = 0
    meses_gracia_parcial: int = 0
    # Costos / gastos iniciales (cada uno financiado o al contado).
    costo_notarial: CostoInicial = field(default_factory=CostoInicial)
    costo_registral: CostoInicial = field(default_factory=CostoInicial)
    costo_tasacion: CostoInicial = field(default_factory=CostoInicial)
    comision_estudio: CostoInicial = field(default_factory=CostoInicial)
    comision_activacion: CostoInicial = field(default_factory=CostoInicial)
    # Costos / gastos periodicos (por cuota).
    gps_periodico: Decimal = CERO
    portes_periodico: Decimal = CERO
    gastos_adm_periodico: Decimal = CERO
    # Seguros: desgravamen como % mensual y riesgo (todo riesgo) como % anual del precio.
    seguro_desgravamen_mensual: Decimal = CERO
    seguro_riesgo_anual: Decimal = CERO
    # Costo de oportunidad del dinero del usuario (TEA) para el VAN.
    cok_anual: Decimal = CERO
    tipo_cambio_referencial: Decimal | None = None
    fecha_inicio: date = field(default_factory=date.today)

    def _costos(self) -> list[CostoInicial]:
        return [
            self.costo_notarial,
            self.costo_registral,
            self.costo_tasacion,
            self.comision_estudio,
            self.comision_activacion,
        ]


@dataclass
class ResultadoSimulacion:
    """Indicadores calculados y cronograma de la simulacion (sin redondear)."""

    moneda: Moneda
    precio_vehiculo: Decimal
    plan: Plan
    numero_cuotas: int
    numero_anios: int
    porcentaje_cuota_inicial: Decimal
    cuota_inicial: Decimal
    porcentaje_cuota_final: Decimal
    cuota_final: Decimal
    monto_prestamo: Decimal
    saldo_financiado: Decimal
    tipo_tasa: TipoTasa
    tasa_ingresada: Decimal
    capitalizacion: Capitalizacion | None
    tea_equivalente: Decimal
    tem: Decimal
    meses_gracia_total: int
    meses_gracia_parcial: int
    seguro_desgravamen_mensual: Decimal
    seguro_riesgo_anual: Decimal
    seguro_riesgo_periodico: Decimal
    gps_periodico: Decimal
    portes_periodico: Decimal
    gastos_adm_periodico: Decimal
    total_costos_financiados: Decimal
    total_costos_efectivo: Decimal
    cuota_mensual: Decimal
    cok_anual: Decimal
    cok_mensual: Decimal
    van: Decimal
    tir_mensual: Decimal | None
    tir_anual: Decimal | None
    tcea: Decimal | None
    total_intereses: Decimal
    total_amortizado: Decimal
    total_seguro_desgravamen: Decimal
    total_seguro_riesgo: Decimal
    total_gps: Decimal
    total_portes: Decimal
    total_gastos_adm: Decimal
    monto_total_pagado: Decimal
    filas: list[FilaCronograma]


def _validar_entrada(entrada: EntradaSimulacion) -> None:
    """Valida las reglas de negocio numericas antes de calcular."""

    if entrada.precio_vehiculo <= CERO:
        raise ValueError("El precio del vehiculo debe ser mayor que cero.")
    if not (CERO <= entrada.porcentaje_cuota_inicial <= UNO):
        raise ValueError("El porcentaje de cuota inicial debe estar entre 0% y 100%.")
    if entrada.valor_tasa < CERO:
        raise ValueError("La tasa de interes no puede ser negativa.")
    if entrada.tipo_tasa == TipoTasa.NOMINAL and entrada.capitalizacion is None:
        raise ValueError("La capitalizacion es obligatoria cuando la tasa es nominal.")

    if entrada.meses_gracia_total < 0 or entrada.meses_gracia_parcial < 0:
        raise ValueError("Los meses de gracia no pueden ser negativos.")
    if entrada.meses_gracia_total + entrada.meses_gracia_parcial >= entrada.plan.numero_cuotas:
        raise ValueError("Los meses de gracia deben ser menores que el numero de cuotas.")

    for nombre, costo in (
        ("notariales", entrada.costo_notarial),
        ("registrales", entrada.costo_registral),
        ("tasacion", entrada.costo_tasacion),
        ("comision de estudio", entrada.comision_estudio),
        ("comision de activacion", entrada.comision_activacion),
    ):
        if costo.monto < CERO:
            raise ValueError(f"El costo de {nombre} no puede ser negativo.")
    for nombre, valor in (
        ("GPS", entrada.gps_periodico),
        ("portes", entrada.portes_periodico),
        ("gastos administrativos", entrada.gastos_adm_periodico),
        ("seguro de desgravamen", entrada.seguro_desgravamen_mensual),
        ("seguro de riesgo", entrada.seguro_riesgo_anual),
        ("COK", entrada.cok_anual),
    ):
        if valor < CERO:
            raise ValueError(f"El valor de {nombre} no puede ser negativo.")


def calcular_simulacion(entrada: EntradaSimulacion) -> ResultadoSimulacion:
    """Calcula todo: montos del producto, el cronograma y los indicadores.

    Pasos: 1) sacar los montos a partir del precio y el plan; 2) pasar la tasa a
    mensual; 3) armar el cronograma mes a mes; 4) con lo que paga la persona,
    calcular VAN, TIR y TCEA (que mide el costo real anual del credito).
    """

    _validar_entrada(entrada)

    # 1) Montos del producto a partir del precio del auto y el plan elegido.
    precio = a_decimal(entrada.precio_vehiculo)
    porcentaje_inicial = a_decimal(entrada.porcentaje_cuota_inicial)
    plan = entrada.plan
    numero_cuotas = plan.numero_cuotas
    porcentaje_final = a_decimal(plan.porcentaje_cuota_final)

    cuota_inicial = precio * porcentaje_inicial   # lo que se adelanta al inicio
    cuota_final = precio * porcentaje_final        # el cuoton (pago grande del final)

    # Los costos iniciales "financiados" se suman al prestamo; los "al contado" no.
    total_financiados = sum((c.monto for c in entrada._costos() if c.financiado), CERO)
    total_efectivo = sum((c.monto for c in entrada._costos() if not c.financiado), CERO)
    monto_prestamo = precio - cuota_inicial + total_financiados
    if monto_prestamo <= CERO:
        raise ValueError(
            "El monto del prestamo debe ser mayor que cero; revise la cuota inicial."
        )

    # 2) La tasa que ingresa el usuario (anual) se pasa a su equivalente mensual.
    tea, tem = servicio_tasas.calcular_tasas_equivalentes(
        entrada.tipo_tasa, entrada.valor_tasa, entrada.capitalizacion
    )

    # El seguro de riesgo se da como % anual del precio; se reparte entre 12 cuotas.
    desgravamen_mensual = a_decimal(entrada.seguro_desgravamen_mensual)
    seguro_riesgo_periodico = a_decimal(entrada.seguro_riesgo_anual) * precio / MESES_ANIO

    parametros = ParametrosCronograma(
        monto_prestamo=monto_prestamo,
        cuota_final=cuota_final,
        tem=tem,
        numero_cuotas=numero_cuotas,
        meses_gracia_total=entrada.meses_gracia_total,
        meses_gracia_parcial=entrada.meses_gracia_parcial,
        seguro_desgravamen_mensual=desgravamen_mensual,
        seguro_riesgo_periodico=seguro_riesgo_periodico,
        gps_periodico=a_decimal(entrada.gps_periodico),
        portes_periodico=a_decimal(entrada.portes_periodico),
        gastos_adm_periodico=a_decimal(entrada.gastos_adm_periodico),
        fecha_inicio=entrada.fecha_inicio,
    )
    # 3) El cronograma mes a mes con las cuotas y el cuoton.
    cronograma = generar_cronograma(parametros)

    # 4) El flujo de caja visto por la persona: en el momento 0 recibe el prestamo
    # (positivo) y despues paga cada mes (negativo). Con eso se sacan VAN/TIR/TCEA.
    flujos = [monto_prestamo]
    flujos.extend(fila.flujo for fila in cronograma.filas)

    cok_anual = a_decimal(entrada.cok_anual)
    cok_mensual = servicio_tasas.anual_a_mensual_compuesta(cok_anual)
    van = servicio_van_tir.calcular_van(flujos, cok_mensual)

    tir_mensual = servicio_van_tir.calcular_tir(flujos)
    tir_anual = (
        potencia(UNO + tir_mensual, MESES_ANIO) - UNO if tir_mensual is not None else None
    )
    # TCEA = costo real anual del credito (la TIR mensual llevada a un ano).
    _, tcea = calcular_tcea(flujos)

    return ResultadoSimulacion(
        moneda=entrada.moneda,
        precio_vehiculo=precio,
        plan=plan,
        numero_cuotas=numero_cuotas,
        numero_anios=plan.numero_anios,
        porcentaje_cuota_inicial=porcentaje_inicial,
        cuota_inicial=cuota_inicial,
        porcentaje_cuota_final=porcentaje_final,
        cuota_final=cuota_final,
        monto_prestamo=monto_prestamo,
        saldo_financiado=cronograma.saldo_financiado,
        tipo_tasa=entrada.tipo_tasa,
        tasa_ingresada=a_decimal(entrada.valor_tasa),
        capitalizacion=entrada.capitalizacion,
        tea_equivalente=tea,
        tem=tem,
        meses_gracia_total=entrada.meses_gracia_total,
        meses_gracia_parcial=entrada.meses_gracia_parcial,
        seguro_desgravamen_mensual=desgravamen_mensual,
        seguro_riesgo_anual=a_decimal(entrada.seguro_riesgo_anual),
        seguro_riesgo_periodico=seguro_riesgo_periodico,
        gps_periodico=a_decimal(entrada.gps_periodico),
        portes_periodico=a_decimal(entrada.portes_periodico),
        gastos_adm_periodico=a_decimal(entrada.gastos_adm_periodico),
        total_costos_financiados=total_financiados,
        total_costos_efectivo=total_efectivo,
        cuota_mensual=cronograma.cuota_ordinaria,
        cok_anual=cok_anual,
        cok_mensual=cok_mensual,
        van=van,
        tir_mensual=tir_mensual,
        tir_anual=tir_anual,
        tcea=tcea,
        total_intereses=cronograma.total_intereses,
        total_amortizado=cronograma.total_amortizado,
        total_seguro_desgravamen=cronograma.total_seguro_desgravamen,
        total_seguro_riesgo=cronograma.total_seguro_riesgo,
        total_gps=cronograma.total_gps,
        total_portes=cronograma.total_portes,
        total_gastos_adm=cronograma.total_gastos_adm,
        monto_total_pagado=cronograma.monto_total_pagado,
        filas=cronograma.filas,
    )


def redondear_fila(fila: FilaCronograma) -> dict:
    """Convierte una fila del cronograma a un diccionario con redondeo de presentacion."""

    return {
        "numero_periodo": fila.numero_periodo,
        "fecha_pago": fila.fecha_pago,
        "tipo_periodo": fila.tipo_periodo,
        "saldo_inicial_cuoton": redondear_moneda(fila.saldo_inicial_cuoton),
        "interes_cuoton": redondear_moneda(fila.interes_cuoton),
        "amortizacion_cuoton": redondear_moneda(fila.amortizacion_cuoton),
        "desgravamen_cuoton": redondear_moneda(fila.desgravamen_cuoton),
        "saldo_final_cuoton": redondear_moneda(fila.saldo_final_cuoton),
        "saldo_inicial": redondear_moneda(fila.saldo_inicial),
        "interes": redondear_moneda(fila.interes),
        "cuota": redondear_moneda(fila.cuota),
        "amortizacion": redondear_moneda(fila.amortizacion),
        "seguro_desgravamen": redondear_moneda(fila.seguro_desgravamen),
        "seguro_riesgo": redondear_moneda(fila.seguro_riesgo),
        "gps": redondear_moneda(fila.gps),
        "portes": redondear_moneda(fila.portes),
        "gastos_adm": redondear_moneda(fila.gastos_adm),
        "saldo_final": redondear_moneda(fila.saldo_final),
        "flujo": redondear_moneda(fila.flujo),
    }


def redondear_cronograma(resultado: ResultadoSimulacion) -> list[dict]:
    """Redondea el cronograma a presentacion (cada fila a dos decimales)."""

    return [redondear_fila(fila) for fila in resultado.filas]


def redondear_resultado(resultado: ResultadoSimulacion) -> dict:
    """Convierte el resultado a un diccionario con redondeo de presentacion."""

    return {
        "moneda": resultado.moneda,
        "precio_vehiculo": redondear_moneda(resultado.precio_vehiculo),
        "plan": resultado.plan,
        "numero_cuotas": resultado.numero_cuotas,
        "numero_anios": resultado.numero_anios,
        "porcentaje_cuota_inicial": redondear_tasa(resultado.porcentaje_cuota_inicial),
        "cuota_inicial": redondear_moneda(resultado.cuota_inicial),
        "porcentaje_cuota_final": redondear_tasa(resultado.porcentaje_cuota_final),
        "cuota_final": redondear_moneda(resultado.cuota_final),
        "monto_prestamo": redondear_moneda(resultado.monto_prestamo),
        "saldo_financiado": redondear_moneda(resultado.saldo_financiado),
        "tipo_tasa": resultado.tipo_tasa,
        "tasa_ingresada": redondear_tasa(resultado.tasa_ingresada),
        "capitalizacion": resultado.capitalizacion,
        "tea_equivalente": redondear_tasa(resultado.tea_equivalente),
        "tem": redondear_tasa(resultado.tem),
        "meses_gracia_total": resultado.meses_gracia_total,
        "meses_gracia_parcial": resultado.meses_gracia_parcial,
        "seguro_desgravamen_mensual": redondear_tasa(resultado.seguro_desgravamen_mensual),
        "seguro_riesgo_anual": redondear_tasa(resultado.seguro_riesgo_anual),
        "seguro_riesgo_periodico": redondear_moneda(resultado.seguro_riesgo_periodico),
        "gps_periodico": redondear_moneda(resultado.gps_periodico),
        "portes_periodico": redondear_moneda(resultado.portes_periodico),
        "gastos_adm_periodico": redondear_moneda(resultado.gastos_adm_periodico),
        "total_costos_financiados": redondear_moneda(resultado.total_costos_financiados),
        "total_costos_efectivo": redondear_moneda(resultado.total_costos_efectivo),
        "cuota_mensual": redondear_moneda(resultado.cuota_mensual),
        "cok_anual": redondear_tasa(resultado.cok_anual),
        "cok_mensual": redondear_tasa(resultado.cok_mensual),
        "van": redondear_moneda(resultado.van),
        "tir_mensual": (
            redondear_tasa(resultado.tir_mensual) if resultado.tir_mensual is not None else None
        ),
        "tir_anual": (
            redondear_tasa(resultado.tir_anual) if resultado.tir_anual is not None else None
        ),
        "tcea": redondear_tasa(resultado.tcea) if resultado.tcea is not None else None,
        "total_intereses": redondear_moneda(resultado.total_intereses),
        "total_amortizado": redondear_moneda(resultado.total_amortizado),
        "total_seguro_desgravamen": redondear_moneda(resultado.total_seguro_desgravamen),
        "total_seguro_riesgo": redondear_moneda(resultado.total_seguro_riesgo),
        "total_gps": redondear_moneda(resultado.total_gps),
        "total_portes": redondear_moneda(resultado.total_portes),
        "total_gastos_adm": redondear_moneda(resultado.total_gastos_adm),
        "monto_total_pagado": redondear_moneda(resultado.monto_total_pagado),
        "cronograma": redondear_cronograma(resultado),
    }
