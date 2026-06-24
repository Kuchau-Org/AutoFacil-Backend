"""Rutas de gestion de clientes (cada asesor ve solo su cartera)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.cliente import ClienteActualizar, ClienteCrear, ClienteRespuesta
from app.modelos.cliente import Cliente
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual
from app.utilidades.respuestas import error_conflicto, error_no_encontrado

enrutador = APIRouter(prefix="/clientes", tags=["Clientes"])


def _obtener_propio(sesion: Session, cliente_id: int, usuario: Usuario) -> Cliente:
    """Obtiene un cliente del propio asesor o lanza 404 si no existe o no es suyo."""

    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None or cliente.usuario_id != usuario.id:
        raise error_no_encontrado("El cliente indicado no existe.")
    return cliente


@enrutador.get("", response_model=list[ClienteRespuesta], summary="Listar y buscar clientes")
def listar_clientes(
    busqueda: str | None = Query(default=None, description="Texto a buscar"),
    incluir_inactivos: bool = Query(default=False),
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> list[Cliente]:
    """Lista los clientes del asesor con busqueda por documento, nombres o apellidos."""

    consulta = sesion.query(Cliente).filter(Cliente.usuario_id == usuario_actual.id)
    if not incluir_inactivos:
        consulta = consulta.filter(Cliente.activo.is_(True))
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            or_(
                Cliente.numero_documento.ilike(patron),
                Cliente.nombres.ilike(patron),
                Cliente.apellidos.ilike(patron),
            )
        )
    return consulta.order_by(Cliente.apellidos, Cliente.nombres).all()


@enrutador.get("/{cliente_id}", response_model=ClienteRespuesta, summary="Obtener un cliente")
def obtener_cliente(
    cliente_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Cliente:
    """Obtiene el detalle de un cliente propio por su identificador."""

    return _obtener_propio(sesion, cliente_id, usuario_actual)


@enrutador.post(
    "",
    response_model=ClienteRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un cliente",
)
def crear_cliente(
    datos: ClienteCrear,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Cliente:
    """Registra un nuevo cliente en la cartera del asesor."""

    duplicado = (
        sesion.query(Cliente)
        .filter(
            Cliente.usuario_id == usuario_actual.id,
            Cliente.numero_documento == datos.numero_documento,
        )
        .first()
    )
    if duplicado is not None:
        raise error_conflicto("Ya tienes un cliente con ese numero de documento.")

    cliente = Cliente(**datos.model_dump(), usuario_id=usuario_actual.id)
    sesion.add(cliente)
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


@enrutador.put("/{cliente_id}", response_model=ClienteRespuesta, summary="Actualizar un cliente")
def actualizar_cliente(
    cliente_id: int,
    datos: ClienteActualizar,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Cliente:
    """Actualiza parcialmente los datos de un cliente propio."""

    cliente = _obtener_propio(sesion, cliente_id, usuario_actual)

    cambios = datos.model_dump(exclude_unset=True)
    if "numero_documento" in cambios and cambios["numero_documento"] != cliente.numero_documento:
        existe = (
            sesion.query(Cliente)
            .filter(
                Cliente.usuario_id == usuario_actual.id,
                Cliente.numero_documento == cambios["numero_documento"],
            )
            .first()
        )
        if existe is not None:
            raise error_conflicto("Ya tienes un cliente con ese numero de documento.")

    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)

    sesion.commit()
    sesion.refresh(cliente)
    return cliente


@enrutador.delete(
    "/{cliente_id}",
    response_model=ClienteRespuesta,
    summary="Desactivar un cliente (baja logica)",
)
def desactivar_cliente(
    cliente_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> Cliente:
    """Desactiva logicamente un cliente propio (no se elimina de la base de datos)."""

    cliente = _obtener_propio(sesion, cliente_id, usuario_actual)
    cliente.activo = False
    sesion.commit()
    sesion.refresh(cliente)
    return cliente
