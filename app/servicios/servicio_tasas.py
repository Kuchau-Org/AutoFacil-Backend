"""Servicio de conversion de tasas de interes.

Centraliza la conversion entre tasa nominal anual (TNA), tasa efectiva anual
(TEA) y tasa efectiva mensual (TEM). Todas las operaciones se realizan con
`Decimal` de alta precision y sin redondeo intermedio.

Convenciones del modelo financiero:
* El cronograma siempre opera con una tasa efectiva mensual (TEM).
* Para tasas efectivas anuales se usa la equivalencia compuesta de 12 periodos.
* Para tasas nominales anuales se convierte primero a TEA segun la
  capitalizacion declarada y luego de TEA a TEM.
"""

from decimal import Decimal

from app.modelos.enumeraciones import Capitalizacion, TipoTasa
from app.utilidades.decimales import MESES_ANIO, UNO, a_decimal, potencia

# Numero de capitalizaciones por anio para cada frecuencia admitida. Se utiliza
# el anio comercial de 360 dias para la capitalizacion diaria, coherente con el
# resto del modelo financiero.
CAPITALIZACIONES_POR_ANIO: dict[Capitalizacion, Decimal] = {
    Capitalizacion.DIARIA: Decimal("360"),
    Capitalizacion.MENSUAL: Decimal("12"),
    Capitalizacion.BIMESTRAL: Decimal("6"),
    Capitalizacion.TRIMESTRAL: Decimal("4"),
    Capitalizacion.CUATRIMESTRAL: Decimal("3"),
    Capitalizacion.SEMESTRAL: Decimal("2"),
    Capitalizacion.ANUAL: Decimal("1"),
}


def convertir_tea_a_tem(tea: Decimal) -> Decimal:
    """Convierte una tasa efectiva anual a tasa efectiva mensual.

    Aplica la equivalencia de tasas: TEM = (1 + TEA)^(1/12) - 1.
    """

    tea = a_decimal(tea)
    exponente = UNO / MESES_ANIO
    return potencia(UNO + tea, exponente) - UNO


def convertir_tna_a_tea(tna: Decimal, capitalizaciones_por_anio: Decimal) -> Decimal:
    """Convierte una tasa nominal anual a tasa efectiva anual.

    Aplica TEA = (1 + TNA/m)^m - 1, donde m es el numero de capitalizaciones
    por anio asociado a la frecuencia de capitalizacion.
    """

    tna = a_decimal(tna)
    m = a_decimal(capitalizaciones_por_anio)
    tasa_por_periodo = tna / m
    return potencia(UNO + tasa_por_periodo, m) - UNO


def obtener_capitalizaciones(capitalizacion: Capitalizacion | None) -> Decimal:
    """Devuelve el numero de capitalizaciones por anio de la frecuencia indicada."""

    if capitalizacion is None:
        raise ValueError(
            "La capitalizacion es obligatoria cuando la tasa es nominal."
        )
    if capitalizacion not in CAPITALIZACIONES_POR_ANIO:
        raise ValueError("La capitalizacion indicada no es valida.")
    return CAPITALIZACIONES_POR_ANIO[capitalizacion]


def calcular_tasas_equivalentes(
    tipo_tasa: TipoTasa,
    valor_tasa: Decimal,
    capitalizacion: Capitalizacion | None = None,
) -> tuple[Decimal, Decimal]:
    """Calcula la TEA y la TEM equivalentes a partir de la tasa ingresada.

    Devuelve la tupla (TEA, TEM). El valor de la tasa se interpreta en formato
    decimal (por ejemplo 0.18 para 18%).
    """

    valor_tasa = a_decimal(valor_tasa)
    if valor_tasa < 0:
        raise ValueError("La tasa de interes no puede ser negativa.")

    if tipo_tasa == TipoTasa.EFECTIVA:
        tea = valor_tasa
    elif tipo_tasa == TipoTasa.NOMINAL:
        m = obtener_capitalizaciones(capitalizacion)
        tea = convertir_tna_a_tea(valor_tasa, m)
    else:
        raise ValueError("El tipo de tasa indicado no es valido.")

    tem = convertir_tea_a_tem(tea)
    return tea, tem


def anual_a_mensual_compuesta(tasa_anual: Decimal) -> Decimal:
    """Convierte cualquier tasa efectiva anual (por ejemplo el COK) a mensual."""

    tasa_anual = a_decimal(tasa_anual)
    exponente = UNO / MESES_ANIO
    return potencia(UNO + tasa_anual, exponente) - UNO


def mensual_a_anual_compuesta(tasa_mensual: Decimal) -> Decimal:
    """Convierte una tasa efectiva mensual a su equivalente efectiva anual."""

    tasa_mensual = a_decimal(tasa_mensual)
    return potencia(UNO + tasa_mensual, MESES_ANIO) - UNO
