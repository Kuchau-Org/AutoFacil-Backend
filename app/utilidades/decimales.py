"""Utilidades de aritmetica decimal de alta precision.

Todo el nucleo financiero de AutoFacil opera con `decimal.Decimal` para
evitar los errores de representacion del tipo `float`. Este modulo centraliza
la configuracion de precision, las conversiones seguras a `Decimal` y las
operaciones que `Decimal` no expone de forma directa (potencias con exponente
fraccionario, redondeo de presentacion, etc.).

Regla general del proyecto: no se redondea ningun valor intermedio. El
redondeo solo se aplica con `redondear_moneda` o `redondear_tasa` al momento
de devolver o mostrar resultados finales.
"""

from decimal import ROUND_HALF_UP, Context, Decimal, getcontext, localcontext

# Precision interna utilizada en los calculos. Es deliberadamente alta para
# conservar la mayor cantidad de cifras significativas posible.
PRECISION_INTERNA = 50

# Se ajusta la precision del contexto global del hilo principal. Las funciones
# que requieren aislamiento usan ademas `localcontext`.
getcontext().prec = PRECISION_INTERNA

# Constantes reutilizadas para evitar instanciaciones repetidas.
CERO = Decimal("0")
UNO = Decimal("1")
CIEN = Decimal("100")
DOCE = Decimal("12")
MESES_ANIO = Decimal("12")


def a_decimal(valor: object) -> Decimal:
    """Convierte un valor arbitrario a `Decimal` de forma segura.

    Los valores `float` se transforman primero a texto para no arrastrar el
    ruido binario propio de la representacion en punto flotante.
    """

    if isinstance(valor, Decimal):
        return valor
    if valor is None:
        return CERO
    if isinstance(valor, float):
        return Decimal(str(valor))
    return Decimal(str(valor))


def potencia(base: Decimal, exponente: Decimal) -> Decimal:
    """Eleva `base` a `exponente` admitiendo exponentes fraccionarios.

    `Decimal` resuelve la potencia general mediante exp(exponente * ln(base)),
    por lo que se exige una base estrictamente positiva cuando el exponente no
    es entero. El calculo se realiza en un contexto local de mayor precision
    para minimizar el error de la aproximacion.
    """

    base = a_decimal(base)
    exponente = a_decimal(exponente)

    if base < CERO and exponente != exponente.to_integral_value():
        raise ValueError(
            "No se puede elevar una base negativa a un exponente fraccionario."
        )

    with localcontext(Context(prec=PRECISION_INTERNA + 10)):
        resultado = base ** exponente
    # Se reduce nuevamente a la precision interna estandar del proyecto.
    return +resultado


def redondear_moneda(valor: object) -> Decimal:
    """Redondea un importe monetario a dos decimales (redondeo medio hacia arriba)."""

    return a_decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def redondear_tasa(valor: object, decimales: int = 7) -> Decimal:
    """Redondea una tasa a la cantidad de decimales indicada para su presentacion."""

    cuantizador = Decimal("1").scaleb(-decimales)
    return a_decimal(valor).quantize(cuantizador, rounding=ROUND_HALF_UP)


def a_float(valor: object) -> float:
    """Convierte un `Decimal` a `float` solo para serializacion o persistencia."""

    return float(a_decimal(valor))
