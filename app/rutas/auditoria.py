"""Rutas de consulta del registro de auditoria del asesor.

Cada asesor ve unicamente la auditoria de sus propias operaciones.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.auditoria import AuditoriaRespuesta
from app.modelos.auditoria import AuditoriaOperacion
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual

enrutador = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@enrutador.get(
    "",
    response_model=list[AuditoriaRespuesta],
    summary="Listar mis registros de auditoria",
)
def listar_auditoria(
    entidad: str | None = Query(default=None, description="Filtrar por entidad"),
    limite: int = Query(default=100, ge=1, le=500),
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> list[AuditoriaOperacion]:
    """Devuelve los registros de auditoria de las operaciones del propio asesor."""

    consulta = sesion.query(AuditoriaOperacion).filter(
        AuditoriaOperacion.usuario_id == usuario_actual.id
    )
    if entidad:
        consulta = consulta.filter(AuditoriaOperacion.entidad == entidad)
    return (
        consulta.order_by(AuditoriaOperacion.fecha_creacion.desc()).limit(limite).all()
    )
