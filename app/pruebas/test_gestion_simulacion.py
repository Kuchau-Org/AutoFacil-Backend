"""Pruebas de la construccion de la entrada de simulacion y la trazabilidad.

Verifican que el precio de la operacion se tome del vehiculo por defecto, pero
que pueda conservarse un precio original (trazabilidad) al recalcular una
simulacion guardada aunque el precio del vehiculo haya cambiado.
"""

from decimal import Decimal

from app.esquemas.simulacion import SimulacionCalcularRequest
from app.modelos.enumeraciones import Moneda
from app.modelos.vehiculo import Vehiculo
from app.servicios.servicio_gestion_simulacion import construir_entrada, convertir_precio


def _solicitud() -> SimulacionCalcularRequest:
    """Crea una solicitud de calculo valida basica."""

    return SimulacionCalcularRequest(
        cliente_id=1,
        vehiculo_id=1,
        moneda="PEN",
        plan="PLAN_36",
        tipo_tasa="EFECTIVA",
        valor_tasa=Decimal("0.15"),
        porcentaje_cuota_inicial=Decimal("0.20"),
    )


def test_entrada_usa_precio_actual_del_vehiculo():
    """Sin precio de operacion explicito se usa el precio actual del vehiculo."""

    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("95000"), moneda=Moneda.SOLES
    )
    entrada = construir_entrada(_solicitud(), vehiculo)
    assert Decimal(entrada.precio_vehiculo) == Decimal("95000")


def test_entrada_conserva_precio_operacion_en_recalculo():
    """Al recalcular se conserva el precio original aunque el vehiculo cambie."""

    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("95000"), moneda=Moneda.SOLES
    )
    entrada = construir_entrada(
        _solicitud(), vehiculo, precio_operacion=Decimal("90000")
    )
    assert Decimal(entrada.precio_vehiculo) == Decimal("90000")


def test_convertir_precio_entre_monedas():
    """El precio del vehiculo se convierte a la moneda del credito con el tipo de cambio."""

    # Mismo signo de moneda: no cambia.
    assert convertir_precio(Decimal("100"), Moneda.SOLES, Moneda.SOLES, None) == Decimal("100")
    # Soles a Dolares: se divide por el tipo de cambio.
    assert convertir_precio(
        Decimal("3750"), Moneda.SOLES, Moneda.DOLARES, Decimal("3.75")
    ) == Decimal("1000")
    # Dolares a Soles: se multiplica por el tipo de cambio.
    assert convertir_precio(
        Decimal("1000"), Moneda.DOLARES, Moneda.SOLES, Decimal("3.75")
    ) == Decimal("3750")


def test_simular_mismo_vehiculo_en_otra_moneda():
    """Un vehiculo en Soles puede simularse en Dolares convirtiendo el precio."""

    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("75000"), moneda=Moneda.SOLES
    )
    solicitud = SimulacionCalcularRequest(
        cliente_id=1,
        vehiculo_id=1,
        moneda="USD",
        tipo_cambio_referencial=Decimal("3.75"),
        plan="PLAN_36",
        tipo_tasa="EFECTIVA",
        valor_tasa=Decimal("0.12"),
        porcentaje_cuota_inicial=Decimal("0.20"),
    )
    entrada = construir_entrada(solicitud, vehiculo)
    assert entrada.moneda == Moneda.DOLARES
    assert Decimal(entrada.precio_vehiculo) == Decimal("20000")  # 75000 / 3.75
