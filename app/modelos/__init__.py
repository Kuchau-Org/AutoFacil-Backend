# Registra todos los modelos ORM antes de crear el esquema.

from app.modelos.cliente import Cliente
from app.modelos.cronograma import CronogramaPago
from app.modelos.enumeraciones import (
    Capitalizacion,
    EstadoSimulacion,
    Moneda,
    Plan,
    TipoPeriodo,
    TipoTasa,
)
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo

__all__ = [
    "Cliente",
    "CronogramaPago",
    "Simulacion",
    "Usuario",
    "Vehiculo",
    "Capitalizacion",
    "EstadoSimulacion",
    "Moneda",
    "Plan",
    "TipoPeriodo",
    "TipoTasa",
]
