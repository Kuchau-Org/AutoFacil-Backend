"""Esquemas Pydantic para la consulta de auditoria de operaciones."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditoriaRespuesta(BaseModel):
    """Representacion de un registro de auditoria para su consulta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    entidad: str
    entidad_id: int | None
    accion: str
    detalle: str | None
    fecha_creacion: datetime
