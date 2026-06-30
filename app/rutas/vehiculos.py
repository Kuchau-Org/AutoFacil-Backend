"""Rutas de los vehiculos del usuario (cada quien ve solo los suyos)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.vehiculo import VehiculoActualizar, VehiculoCrear, VehiculoRespuesta
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import obtener_usuario_actual
from app.utilidades.respuestas import error_no_encontrado

enrutador = APIRouter(prefix="/vehiculos", tags=["Vehiculos"])


def _obtener_propio(sesion: Session, vehiculo_id: int, usuario: Usuario) -> Vehiculo:
    """Obtiene un vehiculo del propio usuario o lanza 404 si no existe o no es suyo."""

    vehiculo = sesion.get(Vehiculo, vehiculo_id)
    if vehiculo is None or vehiculo.usuario_id != usuario.id:
        raise error_no_encontrado("El vehiculo indicado no existe.")
    return vehiculo


@enrutador.get("", response_model=list[VehiculoRespuesta], summary="Listar y buscar vehiculos")
def listar_vehiculos(
    busqueda: str | None = Query(default=None),
    incluir_inactivos: bool = Query(default=False),
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> list[Vehiculo]:
    """Lista los vehiculos del usuario con busqueda por marca, modelo o version."""

    consulta = sesion.query(Vehiculo).filter(Vehiculo.usuario_id == usuario_actual.id)
    if not incluir_inactivos:
        consulta = consulta.filter(Vehiculo.activo.is_(True))
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            or_(
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
                Vehiculo.version.ilike(patron),
            )
        )
    return consulta.order_by(Vehiculo.marca, Vehiculo.modelo).all()


@enrutador.get("/{vehiculo_id}", response_model=VehiculoRespuesta, summary="Obtener un vehiculo")
def obtener_vehiculo(
    vehiculo_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    """Obtiene el detalle de un vehiculo propio por su identificador."""

    return _obtener_propio(sesion, vehiculo_id, usuario_actual)


@enrutador.post(
    "",
    response_model=VehiculoRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un vehiculo",
)
def crear_vehiculo(
    datos: VehiculoCrear,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    """Registra un nuevo vehiculo del usuario."""

    vehiculo = Vehiculo(**datos.model_dump(), usuario_id=usuario_actual.id)
    sesion.add(vehiculo)
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo


@enrutador.put("/{vehiculo_id}", response_model=VehiculoRespuesta, summary="Actualizar un vehiculo")
def actualizar_vehiculo(
    vehiculo_id: int,
    datos: VehiculoActualizar,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    """Actualiza parcialmente los datos de un vehiculo propio."""

    vehiculo = _obtener_propio(sesion, vehiculo_id, usuario_actual)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(vehiculo, campo, valor)
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo


@enrutador.delete(
    "/{vehiculo_id}",
    response_model=VehiculoRespuesta,
    summary="Desactivar un vehiculo (baja logica)",
)
def desactivar_vehiculo(
    vehiculo_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    """Desactiva logicamente un vehiculo propio del catalogo."""

    vehiculo = _obtener_propio(sesion, vehiculo_id, usuario_actual)
    vehiculo.activo = False
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo
