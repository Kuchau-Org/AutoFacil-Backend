"""Servicio de tipo de cambio en tiempo real.

Consulta una API publica y gratuita de tasas de cambio (open.er-api.com) para
obtener el valor actual de las monedas. Mantiene una pequena cache en memoria
para no llamar a la API en cada solicitud y, si la consulta falla (por ejemplo,
sin conexion a internet), informa claramente que el dato proviene de la cache o
de un respaldo local en lugar de presentarlo como informacion en linea.

El tipo de cambio es solo informativo: el calculo de la simulacion siempre se
realiza en la moneda del credito, sin conversiones silenciosas.
"""

from __future__ import annotations

import time
from decimal import Decimal

import httpx

# Solo se admiten las monedas usadas por la aplicacion.
MONEDAS_VALIDAS = {"USD", "PEN"}

# Proveedor publico y sin clave de tasas de cambio.
_URL_PROVEEDOR = "https://open.er-api.com/v6/latest/{base}"
_FUENTE_LINEA = "open.er-api.com"

# Vigencia de la cache en segundos (las tasas se actualizan, a lo sumo, cada dia).
_TTL_CACHE = 60 * 60

# Valores referenciales por defecto si la API no responde (aprox. 2026).
_TASAS_POR_DEFECTO: dict[str, dict[str, Decimal]] = {
    "USD": {"PEN": Decimal("3.75")},
    "PEN": {"USD": Decimal("0.2667")},
}

# Cache simple en memoria: base -> (instante, {moneda: tasa}).
_cache: dict[str, tuple[float, dict[str, Decimal]]] = {}


class ParMonedaInvalido(ValueError):
    """Se solicito un par de monedas no soportado por la aplicacion."""


def _consultar_proveedor(base: str) -> dict[str, Decimal] | None:
    """Llama a la API publica y devuelve el mapa de tasas, o None si falla."""

    try:
        respuesta = httpx.get(_URL_PROVEEDOR.format(base=base), timeout=5.0)
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
    except (httpx.HTTPError, ValueError):
        return None
    if cuerpo.get("result") != "success":
        return None
    tasas_crudas = cuerpo.get("rates") or {}
    return {moneda: Decimal(str(valor)) for moneda, valor in tasas_crudas.items()}


def _obtener_tasas(base: str) -> tuple[dict[str, Decimal], str]:
    """Devuelve las tasas de la base indicada y el origen del dato.

    El origen es uno de: "linea" (consulta exitosa), "cache" (consulta fallida
    pero hay cache previa) o "local" (sin cache; respaldo por defecto).
    """

    ahora = time.monotonic()
    en_cache = _cache.get(base)
    if en_cache and ahora - en_cache[0] < _TTL_CACHE:
        return en_cache[1], "linea"

    tasas = _consultar_proveedor(base)
    if tasas:
        _cache[base] = (ahora, tasas)
        return tasas, "linea"

    # La consulta fallo: usar cache vencida si existe, marcandola como tal.
    if en_cache:
        return en_cache[1], "cache"
    return _TASAS_POR_DEFECTO.get(base, {}), "local"


def obtener_tipo_cambio(base: str, destino: str) -> dict:
    """Obtiene el tipo de cambio de `base` a `destino` (solo USD y PEN).

    Lanza `ParMonedaInvalido` si alguna moneda no es soportada, en lugar de
    devolver una tasa enganosa (por ejemplo 1) para un par invalido.
    """

    base = (base or "").upper().strip()
    destino = (destino or "").upper().strip()
    if base not in MONEDAS_VALIDAS or destino not in MONEDAS_VALIDAS:
        raise ParMonedaInvalido(
            "Solo se admite la conversion entre Soles (PEN) y Dolares (USD)."
        )

    if base == destino:
        return {
            "base": base,
            "destino": destino,
            "tasa": Decimal("1"),
            "fuente": "par identico",
            "en_linea": True,
        }

    tasas, origen = _obtener_tasas(base)
    tasa = tasas.get(destino)
    if tasa is None:
        # Sin dato del proveedor para el par: respaldo local.
        tasa = _TASAS_POR_DEFECTO.get(base, {}).get(destino)
        origen = "local"
    if tasa is None:
        raise ParMonedaInvalido(
            "No hay tipo de cambio disponible para el par solicitado."
        )

    fuente = {
        "linea": _FUENTE_LINEA,
        "cache": "cache (dato no actualizado)",
        "local": "valor referencial local",
    }[origen]

    return {
        "base": base,
        "destino": destino,
        "tasa": tasa,
        "fuente": fuente,
        "en_linea": origen == "linea",
    }
