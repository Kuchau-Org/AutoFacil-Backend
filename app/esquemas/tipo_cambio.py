"""Esquema de respuesta del tipo de cambio."""

from pydantic import BaseModel

from app.esquemas.comunes import DecimalNumero


class TipoCambioRespuesta(BaseModel):
    """Tipo de cambio referencial entre dos monedas."""

    base: str
    destino: str
    tasa: DecimalNumero
    fuente: str
    en_linea: bool
