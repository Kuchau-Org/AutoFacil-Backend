"""Rutas publicas de consulta compartible para el cliente final.

Estas rutas no requieren autenticacion: permiten que el asesor comparta con el
cliente un enlace de solo lectura con el resumen del financiamiento y el
cronograma. El acceso se realiza mediante un token firmado que incorpora el
identificador de la simulacion.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.esquemas.simulacion import SimulacionClienteVista
from app.modelos.enumeraciones import EstadoSimulacion
from app.modelos.simulacion import Simulacion
from fastapi import HTTPException, status

from app.seguridad.jwt import leer_token_compartir
from app.utilidades.respuestas import error_no_encontrado

enrutador = APIRouter(prefix="/publico", tags=["Vista del cliente"])

# Estados cuya propuesta NO debe quedar accesible por el enlace publico. Una
# propuesta archivada no es una oferta vigente para el cliente, asi que el enlace
# responde 410 aunque el token siga firmado.
_MOTIVO_NO_COMPARTIBLE = {
    EstadoSimulacion.ARCHIVADA: "La propuesta fue archivada y el enlace ya no esta disponible.",
}


@enrutador.get(
    "/simulaciones/{token}",
    response_model=SimulacionClienteVista,
    summary="Consulta publica de una simulacion compartida",
)
def consultar_simulacion_compartida(
    token: str,
    sesion: Session = Depends(obtener_sesion),
) -> SimulacionClienteVista:
    """Devuelve la vista de cliente de una simulacion a partir de su token.

    El token es el enlace compartible generado por el asesor. No expone datos
    internos del sistema ni requiere iniciar sesion.
    """

    simulacion_id, expirado = leer_token_compartir(token)
    if expirado:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="El enlace de la simulacion ha expirado. Solicite uno nuevo al asesor.",
        )
    if simulacion_id is None:
        raise error_no_encontrado("El enlace de la simulacion no es valido.")

    simulacion = sesion.get(Simulacion, simulacion_id)
    if simulacion is None:
        raise error_no_encontrado("La simulacion compartida no existe.")

    # Solo las propuestas vigentes (calculadas) se muestran al cliente.
    motivo = _MOTIVO_NO_COMPARTIBLE.get(simulacion.estado)
    if motivo is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=motivo)

    return SimulacionClienteVista(
        codigo=simulacion.codigo,
        nombre=simulacion.nombre,
        estado=simulacion.estado,
        moneda=simulacion.moneda,
        cliente_nombre=(
            f"{simulacion.cliente.nombres} {simulacion.cliente.apellidos}"
            if simulacion.cliente
            else None
        ),
        vehiculo_descripcion=(
            f"{simulacion.vehiculo.marca} {simulacion.vehiculo.modelo}"
            if simulacion.vehiculo
            else None
        ),
        fecha_inicio=simulacion.fecha_inicio,
        precio_vehiculo=float(simulacion.precio_vehiculo),
        cuota_inicial=float(simulacion.cuota_inicial),
        cuota_final=float(simulacion.cuota_final),
        monto_financiado=float(simulacion.monto_financiado),
        plazo_meses=simulacion.plazo_meses,
        tea_equivalente=float(simulacion.tea_equivalente),
        tem=float(simulacion.tem),
        cuota_mensual=float(simulacion.cuota_mensual),
        cuota_total_promedio=float(simulacion.cuota_total_promedio),
        tcea=float(simulacion.tcea) if simulacion.tcea is not None else None,
        tasa_moratoria_anual=float(simulacion.tasa_moratoria_anual),
        costo_total_credito=float(simulacion.costo_total_credito),
        total_intereses=float(simulacion.total_intereses),
        total_seguros=float(simulacion.total_seguros),
        total_gastos_iniciales=float(simulacion.gastos_iniciales),
        total_cargos_desembolso=float(simulacion.total_cargos_desembolso),
        total_gps_mantenimiento=float(simulacion.total_gps_mantenimiento),
        monto_total_pagado=float(simulacion.monto_total_pagado),
        seguro_desgravamen_anual=float(simulacion.seguro_desgravamen_anual),
        desgravamen_consentido=simulacion.desgravamen_consentido,
        seguro_vehicular_mensual=float(simulacion.seguro_vehicular_mensual),
        gps_instalacion=float(simulacion.gps_instalacion),
        gps_mantenimiento_mensual=float(simulacion.gps_mantenimiento_mensual),
        gps_reposicion=float(simulacion.gps_reposicion),
        gastos_notariales=float(simulacion.gastos_notariales),
        gastos_registrales=float(simulacion.gastos_registrales),
        tasacion=float(simulacion.tasacion),
        aseguradora=simulacion.aseguradora,
        numero_poliza=simulacion.numero_poliza,
        coberturas=simulacion.coberturas,
        cronograma=[
            CronogramaFilaRespuesta.model_validate(fila)
            for fila in simulacion.cronograma
        ],
    )
