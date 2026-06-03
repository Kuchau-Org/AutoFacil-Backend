"""Rutas de indicadores agregados del asesor para el panel principal."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.simulacion import SimulacionListado
from app.modelos.cliente import Cliente
from app.modelos.enumeraciones import EstadoSimulacion, Moneda
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import obtener_usuario_actual

enrutador = APIRouter(prefix="/indicadores", tags=["Indicadores financieros"])

# Estados que no cuentan en los indicadores agregados (las archivadas se omiten).
_ESTADOS_EXCLUIDOS = [EstadoSimulacion.ARCHIVADA]


class TotalPorMoneda(BaseModel):
    """Monto financiado total acumulado para una moneda especifica."""

    moneda: Moneda
    monto_total_financiado: float
    cantidad: int


class ResumenDashboard(BaseModel):
    """Resumen agregado de las operaciones del asesor."""

    total_clientes: int
    total_vehiculos: int
    total_simulaciones: int
    promedio_tcea: float | None
    # El monto financiado se agrupa por moneda: nunca se suman PEN y USD juntos.
    montos_por_moneda: list[TotalPorMoneda]
    simulaciones_recientes: list[SimulacionListado]


@enrutador.get(
    "/resumen",
    response_model=ResumenDashboard,
    summary="Resumen del panel principal",
)
def obtener_resumen(
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> ResumenDashboard:
    """Calcula los indicadores agregados del asesor para el panel principal."""

    uid = usuario_actual.id
    total_clientes = (
        sesion.query(func.count(Cliente.id))
        .filter(Cliente.usuario_id == uid, Cliente.activo.is_(True))
        .scalar()
        or 0
    )
    total_vehiculos = (
        sesion.query(func.count(Vehiculo.id))
        .filter(Vehiculo.usuario_id == uid, Vehiculo.activo.is_(True))
        .scalar()
        or 0
    )
    # Los agregados excluyen simulaciones anuladas o rechazadas.
    vigentes = (Simulacion.usuario_id == uid, Simulacion.estado.notin_(_ESTADOS_EXCLUIDOS))
    total_simulaciones = (
        sesion.query(func.count(Simulacion.id)).filter(*vigentes).scalar() or 0
    )
    # La TCEA es una tasa, por lo que su promedio si tiene sentido entre monedas.
    promedio_tcea = sesion.query(func.avg(Simulacion.tcea)).filter(*vigentes).scalar()

    # Los montos financiados se agrupan por moneda; no se mezclan PEN y USD.
    filas_moneda = (
        sesion.query(
            Simulacion.moneda,
            func.coalesce(func.sum(Simulacion.monto_financiado), 0),
            func.count(Simulacion.id),
        )
        .filter(*vigentes)
        .group_by(Simulacion.moneda)
        .all()
    )
    montos_por_moneda = [
        TotalPorMoneda(
            moneda=moneda, monto_total_financiado=float(monto), cantidad=int(cantidad)
        )
        for moneda, monto, cantidad in filas_moneda
    ]

    # Las recientes del panel muestran solo propuestas vigentes (no archivadas).
    recientes = (
        sesion.query(Simulacion)
        .filter(*vigentes)
        .order_by(Simulacion.fecha_creacion.desc())
        .limit(5)
        .all()
    )
    from app.rutas.simulaciones import _a_listado

    return ResumenDashboard(
        total_clientes=int(total_clientes),
        total_vehiculos=int(total_vehiculos),
        total_simulaciones=int(total_simulaciones),
        promedio_tcea=float(promedio_tcea) if promedio_tcea is not None else None,
        montos_por_moneda=montos_por_moneda,
        simulaciones_recientes=[_a_listado(simulacion) for simulacion in recientes],
    )
