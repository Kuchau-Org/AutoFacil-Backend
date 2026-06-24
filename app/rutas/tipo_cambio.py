"""Ruta de consulta del tipo de cambio en tiempo real (USD/PEN)."""

from fastapi import APIRouter, Depends, Query

from app.esquemas.tipo_cambio import TipoCambioRespuesta
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual
from app.servicios.servicio_tipo_cambio import ParMonedaInvalido, obtener_tipo_cambio
from app.utilidades.respuestas import error_validacion

enrutador = APIRouter(prefix="/tipo-cambio", tags=["Tipo de cambio"])


@enrutador.get(
    "",
    response_model=TipoCambioRespuesta,
    summary="Consultar el tipo de cambio en tiempo real",
)
def consultar_tipo_cambio(
    base: str = Query(default="USD", description="Moneda de origen: USD o PEN."),
    destino: str = Query(default="PEN", description="Moneda de destino: USD o PEN."),
    _: Usuario = Depends(obtener_usuario_actual),
) -> dict:
    """Devuelve el tipo de cambio referencial entre Soles y Dolares.

    Solo admite los pares USD/PEN y PEN/USD; cualquier otra moneda devuelve 400.
    """

    try:
        return obtener_tipo_cambio(base, destino)
    except ParMonedaInvalido as exc:
        raise error_validacion(str(exc)) from exc
