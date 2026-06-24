"""Aritmetica decimal de alta precision (conversiones, potencias, redondeo)."""

from decimal import ROUND_HALF_UP, Context, Decimal, getcontext, localcontext

PRECISION_INTERNA = 50
getcontext().prec = PRECISION_INTERNA

CERO = Decimal("0")
UNO = Decimal("1")
MESES_ANIO = Decimal("12")


def a_decimal(valor: object) -> Decimal:
    """Convierte un valor a Decimal de forma segura (los float pasan por texto)."""

    if isinstance(valor, Decimal):
        return valor
    if valor is None:
        return CERO
    if isinstance(valor, float):
        return Decimal(str(valor))
    return Decimal(str(valor))


def potencia(base: Decimal, exponente: Decimal) -> Decimal:
    """Eleva base a exponente admitiendo exponentes fraccionarios."""

    base = a_decimal(base)
    exponente = a_decimal(exponente)

    if base < CERO and exponente != exponente.to_integral_value():
        raise ValueError(
            "No se puede elevar una base negativa a un exponente fraccionario."
        )

    with localcontext(Context(prec=PRECISION_INTERNA + 10)):
        resultado = base ** exponente
    return +resultado


def redondear_moneda(valor: object) -> Decimal:
    """Redondea un importe monetario a dos decimales (redondeo medio hacia arriba)."""

    return a_decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def redondear_tasa(valor: object, decimales: int = 7) -> Decimal:
    """Redondea una tasa a la cantidad de decimales indicada para su presentacion."""

    cuantizador = Decimal("1").scaleb(-decimales)
    return a_decimal(valor).quantize(cuantizador, rounding=ROUND_HALF_UP)
