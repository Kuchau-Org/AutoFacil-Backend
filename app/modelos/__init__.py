"""Registro central de los modelos ORM de AutoFacil.

Importar este paquete asegura que SQLAlchemy conozca todas las tablas antes de
crear el esquema de la base de datos.
"""

from app.modelos.auditoria import AuditoriaOperacion
from app.modelos.cliente import Cliente
from app.modelos.cronograma import CronogramaPago
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    TipoGracia,
    TipoPeriodo,
    TipoTasa,
)
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo

__all__ = [
    "AuditoriaOperacion",
    "Cliente",
    "CronogramaPago",
    "Simulacion",
    "Usuario",
    "Vehiculo",
    "Capitalizacion",
    "EstadoSimulacion",
    "Moneda",
    "TipoGracia",
    "TipoPeriodo",
    "TipoTasa",
]
