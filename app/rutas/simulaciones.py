"""Rutas de calculo y gestion de simulaciones de credito vehicular.

Cada asesor gestiona sus propias simulaciones: se filtran por `usuario_id` y una
simulacion solo es accesible (ver, editar, recalcular, eliminar) por el asesor
que la creo. El cliente y el vehiculo usados tambien deben ser del asesor.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.esquemas.simulacion import (
    ResultadoCalculo,
    SimulacionCalcularRequest,
    SimulacionDetalle,
    SimulacionGuardarRequest,
    SimulacionListado,
    SimulacionRespuesta,
)
from app.modelos.cliente import Cliente
from app.modelos.enumeraciones import EstadoSimulacion
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import obtener_usuario_actual
from app.servicios.servicio_auditoria import registrar_auditoria
from app.servicios.servicio_gestion_simulacion import (
    aplicar_resultado_a_modelo,
    calcular_desde_solicitud,
    construir_filas_cronograma,
    convertir_precio,
)
from app.servicios.servicio_simulacion import redondear_resultado
from app.utilidades.respuestas import error_no_encontrado, error_validacion

enrutador = APIRouter(prefix="/simulaciones", tags=["Simulaciones"])


def _validar_para_crear(
    sesion: Session, solicitud: SimulacionCalcularRequest, usuario: Usuario
) -> Vehiculo:
    """Valida una NUEVA simulacion: cliente y vehiculo del asesor y activos.

    Cualquier vehiculo activo del asesor se puede simular. La moneda del credito
    puede diferir de la del vehiculo (se convierte con el tipo de cambio).
    Devuelve el vehiculo.
    """

    cliente = sesion.get(Cliente, solicitud.cliente_id)
    if cliente is None or cliente.usuario_id != usuario.id or not cliente.activo:
        raise error_validacion("El cliente seleccionado no existe o esta inactivo.")
    vehiculo = sesion.get(Vehiculo, solicitud.vehiculo_id)
    if vehiculo is None or vehiculo.usuario_id != usuario.id or not vehiculo.activo:
        raise error_validacion("El vehiculo seleccionado no existe o esta inactivo.")
    return vehiculo


def _vehiculo_de_simulacion(
    sesion: Session, solicitud: SimulacionCalcularRequest, usuario: Usuario
) -> Vehiculo:
    """Obtiene el vehiculo para previsualizar, editar o recalcular una simulacion.

    Solo comprueba que el cliente y el vehiculo pertenezcan al asesor. A
    diferencia de crear una propuesta nueva, aqui NO se exige que el vehiculo
    siga activo: asi se puede previsualizar, editar y recalcular una propuesta
    ya registrada aunque su vehiculo se haya dado de baja despues.
    """

    # Se busca el cliente por su id y se valida que sea del asesor actual (no se
    # puede operar sobre datos de otro usuario).
    cliente = sesion.get(Cliente, solicitud.cliente_id)
    if cliente is None or cliente.usuario_id != usuario.id:
        raise error_validacion("El cliente de la simulacion ya no existe.")
    vehiculo = sesion.get(Vehiculo, solicitud.vehiculo_id)
    if vehiculo is None or vehiculo.usuario_id != usuario.id:
        raise error_validacion("El vehiculo de la simulacion ya no existe.")
    return vehiculo


def _obtener_simulacion(sesion: Session, simulacion_id: int, usuario: Usuario) -> Simulacion:
    """Obtiene una simulacion propia o lanza 404 si no existe o no es del asesor."""

    simulacion = sesion.get(Simulacion, simulacion_id)
    if simulacion is None or simulacion.usuario_id != usuario.id:
        raise error_no_encontrado("La simulacion indicada no existe.")
    return simulacion


def _a_detalle(simulacion: Simulacion) -> SimulacionDetalle:
    """Construye la representacion detallada de una simulacion."""

    base = SimulacionRespuesta.model_validate(simulacion).model_dump()
    return SimulacionDetalle(
        **base,
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
        usuario_nombre=(
            f"{simulacion.usuario.nombre} {simulacion.usuario.apellido}"
            if simulacion.usuario
            else None
        ),
        cronograma=[
            CronogramaFilaRespuesta.model_validate(fila)
            for fila in simulacion.cronograma
        ],
    )


def _a_listado(simulacion: Simulacion) -> SimulacionListado:
    """Construye el resumen de una simulacion para listados."""

    return SimulacionListado(
        id=simulacion.id,
        codigo=simulacion.codigo,
        nombre=simulacion.nombre,
        estado=simulacion.estado,
        moneda=simulacion.moneda,
        cliente_id=simulacion.cliente_id,
        vehiculo_id=simulacion.vehiculo_id,
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
        monto_financiado=float(simulacion.monto_financiado),
        plazo_meses=simulacion.plazo_meses,
        cuota_mensual=float(simulacion.cuota_mensual),
        tcea=float(simulacion.tcea) if simulacion.tcea is not None else None,
        fecha_creacion=simulacion.fecha_creacion,
    )


def _solicitud_desde_modelo(simulacion: Simulacion) -> SimulacionCalcularRequest:
    """Reconstruye la solicitud de calculo a partir de una simulacion guardada."""

    return SimulacionCalcularRequest(
        cliente_id=simulacion.cliente_id,
        vehiculo_id=simulacion.vehiculo_id,
        nombre=simulacion.nombre,
        moneda=simulacion.moneda,
        tipo_cambio_referencial=simulacion.tipo_cambio_referencial,
        tipo_tasa=simulacion.tipo_tasa,
        valor_tasa=simulacion.tasa_ingresada,
        capitalizacion=simulacion.capitalizacion,
        plazo_meses=simulacion.plazo_meses,
        porcentaje_cuota_inicial=simulacion.porcentaje_cuota_inicial,
        porcentaje_cuota_final=simulacion.porcentaje_cuota_final,
        tipo_gracia=simulacion.tipo_gracia,
        meses_gracia=simulacion.meses_gracia,
        seguro_desgravamen_anual=simulacion.seguro_desgravamen_anual,
        desgravamen_consentido=simulacion.desgravamen_consentido,
        seguro_vehicular_mensual=simulacion.seguro_vehicular_mensual,
        gps_instalacion=simulacion.gps_instalacion,
        gps_mantenimiento_mensual=simulacion.gps_mantenimiento_mensual,
        gps_reposicion=simulacion.gps_reposicion,
        gastos_notariales=simulacion.gastos_notariales,
        gastos_registrales=simulacion.gastos_registrales,
        tasacion=simulacion.tasacion,
        cok_anual=simulacion.cok_anual,
        tasa_descuento_van=simulacion.tasa_descuento_van,
        tasa_moratoria_anual=simulacion.tasa_moratoria_anual,
        aseguradora=simulacion.aseguradora,
        numero_poliza=simulacion.numero_poliza,
        coberturas=simulacion.coberturas,
        fecha_inicio=simulacion.fecha_inicio,
    )


@enrutador.get("", response_model=list[SimulacionListado], summary="Listar simulaciones")
def listar_simulaciones(
    busqueda: str | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
    vehiculo_id: int | None = Query(default=None),
    estado: EstadoSimulacion | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> list[SimulacionListado]:
    """Lista las simulaciones del asesor con busqueda y filtros opcionales.

    Permite filtrar por cliente, vehiculo y estado, ademas de la busqueda libre
    por nombre, codigo, datos del cliente o del vehiculo.
    """

    consulta = (
        sesion.query(Simulacion)
        .filter(Simulacion.usuario_id == usuario_actual.id)
        .outerjoin(Cliente, Simulacion.cliente_id == Cliente.id)
        .outerjoin(Vehiculo, Simulacion.vehiculo_id == Vehiculo.id)
    )
    if cliente_id is not None:
        consulta = consulta.filter(Simulacion.cliente_id == cliente_id)
    if vehiculo_id is not None:
        consulta = consulta.filter(Simulacion.vehiculo_id == vehiculo_id)
    if estado is not None:
        consulta = consulta.filter(Simulacion.estado == estado)
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            or_(
                Simulacion.nombre.ilike(patron),
                Simulacion.codigo.ilike(patron),
                Cliente.nombres.ilike(patron),
                Cliente.apellidos.ilike(patron),
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
            )
        )

    simulaciones = consulta.order_by(Simulacion.fecha_creacion.desc()).all()
    return [_a_listado(simulacion) for simulacion in simulaciones]


@enrutador.post(
    "/calcular",
    response_model=ResultadoCalculo,
    summary="Calcular simulacion sin guardar (previsualizacion)",
)
def calcular_simulacion_preview(
    solicitud: SimulacionCalcularRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> dict:
    """Calcula una simulacion sin persistirla, util para previsualizar resultados.

    La previsualizacion solo exige que el cliente y el vehiculo sean del asesor
    (no que el vehiculo siga activo), para poder previsualizar la edicion de una
    propuesta historica cuyo vehiculo se dio de baja.
    """

    vehiculo = _vehiculo_de_simulacion(sesion, solicitud, usuario_actual)
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc
    return redondear_resultado(resultado)


@enrutador.post(
    "",
    response_model=SimulacionDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Calcular y guardar una simulacion",
)
def crear_simulacion(
    solicitud: SimulacionGuardarRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Calcula y guarda una nueva simulacion junto con su cronograma."""

    vehiculo = _validar_para_crear(sesion, solicitud, usuario_actual)
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    # Codigo temporal unico para no chocar con la restriccion unique antes de
    # conocer el id definitivo; se reemplaza por SIM-###### tras el flush.
    simulacion = Simulacion(
        codigo=f"TMP-{uuid4().hex}",
        cliente_id=solicitud.cliente_id,
        vehiculo_id=solicitud.vehiculo_id,
        usuario_id=usuario_actual.id,
        estado=solicitud.estado,
    )
    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    sesion.add(simulacion)
    sesion.flush()
    simulacion.codigo = f"SIM-{simulacion.id:06d}"
    simulacion.cronograma = construir_filas_cronograma(resultado)
    registrar_auditoria(
        sesion, usuario_actual.id, "Simulacion", "CREAR", simulacion.id, simulacion.codigo
    )
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.get(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Obtener detalle de una simulacion",
)
def obtener_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Obtiene el detalle completo de una simulacion propia, incluido el cronograma."""

    return _a_detalle(_obtener_simulacion(sesion, simulacion_id, usuario_actual))


@enrutador.put(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Editar parametros y recalcular una simulacion",
)
def actualizar_simulacion(
    simulacion_id: int,
    solicitud: SimulacionGuardarRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Edita los parametros de una simulacion propia y recalcula su cronograma.

    Se permite editar aunque el vehiculo ya se haya dado de baja (este inactivo).
    Por defecto se conserva el precio original de la propuesta; solo se actualiza
    al precio actual del vehiculo si la solicitud lo pide (`actualizar_precio`).
    """

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    vehiculo = _vehiculo_de_simulacion(sesion, solicitud, usuario_actual)
    # Si se pide actualizar el precio, se reconvierte desde el precio actual del
    # vehiculo. Si no, se conserva el precio original; pero ese precio esta en la
    # moneda original de la propuesta, asi que si la moneda del credito cambia hay
    # que convertirlo a la nueva moneda para no corromper el importe.
    if solicitud.actualizar_precio:
        precio_operacion = None
    else:
        precio_operacion = convertir_precio(
            simulacion.precio_vehiculo,
            simulacion.moneda,
            solicitud.moneda,
            solicitud.tipo_cambio_referencial,
        )
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo, precio_operacion=precio_operacion)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    simulacion.cliente_id = solicitud.cliente_id
    simulacion.vehiculo_id = solicitud.vehiculo_id
    # Editar y recalcular NO cambia el estado de la simulacion.
    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    simulacion.cronograma = construir_filas_cronograma(resultado)
    registrar_auditoria(
        sesion, usuario_actual.id, "Simulacion", "ACTUALIZAR", simulacion.id, simulacion.codigo
    )
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.post(
    "/{simulacion_id}/recalcular",
    response_model=SimulacionDetalle,
    summary="Recalcular una simulacion con sus parametros guardados",
)
def recalcular_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Recalcula una simulacion propia usando sus parametros almacenados."""

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    # Se reconstruye la solicitud de calculo a partir de lo guardado en la base.
    solicitud = _solicitud_desde_modelo(simulacion)
    # Recalcular funciona sobre propuestas historicas aunque el vehiculo ya se
    # haya dado de baja; solo exige que cliente y vehiculo sean del asesor.
    vehiculo = _vehiculo_de_simulacion(sesion, solicitud, usuario_actual)
    try:
        # Se conserva el precio original de la operacion para mantener la
        # trazabilidad: recalcular no cambia el precio con el que se pacto.
        resultado = calcular_desde_solicitud(
            solicitud, vehiculo, precio_operacion=simulacion.precio_vehiculo
        )
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    simulacion.cronograma = construir_filas_cronograma(resultado)
    registrar_auditoria(
        sesion, usuario_actual.id, "Simulacion", "RECALCULAR", simulacion.id, simulacion.codigo
    )
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.delete(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Archivar una simulacion (baja logica)",
)
def archivar_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Archiva una simulacion propia (baja logica): conserva el registro y su
    historial, pero la marca como ARCHIVADA y deja de ser compartible. No hay
    borrado definitivo, para conservar las operaciones registradas.
    """

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    simulacion.estado = EstadoSimulacion.ARCHIVADA
    registrar_auditoria(
        sesion, usuario_actual.id, "Simulacion", "ARCHIVAR", simulacion.id, simulacion.codigo
    )
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)
