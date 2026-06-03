"""Servicio de registro de auditoria de operaciones."""

from sqlalchemy.orm import Session

from app.modelos.auditoria import AuditoriaOperacion


def registrar_auditoria(
    sesion: Session,
    usuario_id: int | None,
    entidad: str,
    accion: str,
    entidad_id: int | None = None,
    detalle: str | None = None,
) -> None:
    """Inserta un registro de auditoria sin confirmar la transaccion.

    El commit queda a cargo del flujo que invoca la operacion principal, de modo
    que la auditoria comparta la misma transaccion que la accion auditada.
    """

    registro = AuditoriaOperacion(
        usuario_id=usuario_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        detalle=detalle,
    )
    sesion.add(registro)
