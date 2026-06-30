"""Datos semilla para ejecucion local (idempotente)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import FabricaSesion, crear_tablas
from app.esquemas.simulacion import SimulacionGuardarRequest
from app.modelos.enumeraciones import Capitalizacion, EstadoSimulacion, Moneda, Plan, TipoTasa
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.hash import hashear_password
from app.servicios.servicio_gestion_simulacion import (
    aplicar_resultado_a_modelo,
    calcular_desde_solicitud,
    construir_filas_cronograma,
)


# Vehiculos de ejemplo (cada usuario recibe su propia copia).
_VEHICULOS = [
    {
        "marca": "Toyota", "modelo": "Corolla Cross", "version": "XLI", "anio": 2026,
        "tipo": "SUV", "precio": Decimal("90000.00"), "moneda": Moneda.SOLES,
        "descripcion": "SUV compacto, ideal para la ciudad y el uso diario.",
        "url_imagen": (
            "https://northperurentacar.com.pe/wp-content/uploads/2023/05/"
            "alquiler-de-autos-toyota-corolla-cross-talara-piura-peru.jpg"
        ),
    },
    {
        "marca": "Hyundai", "modelo": "Tucson", "version": "GLS 2.0", "anio": 2025,
        "tipo": "SUV", "precio": Decimal("35000.00"), "moneda": Moneda.DOLARES,
        "descripcion": "SUV familiar con buen equipamiento.",
        "url_imagen": (
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:"
            "ANd9GcSBVablpp4RF9SzGTgASPyBx5tgn7CiAo_58w&s"
        ),
    },
    {
        "marca": "Kia", "modelo": "Rio", "version": "LX", "anio": 2025,
        "tipo": "Sedan", "precio": Decimal("62000.00"), "moneda": Moneda.SOLES,
        "descripcion": "Sedan economico de bajo consumo de combustible.",
        "url_imagen": "https://www.diariomotor.com/imagenes/2020/05/kia-rio-2020-4.jpg?class=M",
    },
    {
        "marca": "Volkswagen", "modelo": "Virtus", "version": "Comfortline", "anio": 2026,
        "tipo": "Sedan", "precio": Decimal("85000.00"), "moneda": Moneda.SOLES,
        "descripcion": "Sedan con tecnologia de seguridad avanzada.",
        "url_imagen": (
            "https://fotos.perfil.com/2018/03/01/trim/1280/720/"
            "5e7d61736d1c41d2c0bb03737267bad2-low.jpg"
        ),
    },
    {
        "marca": "Mazda", "modelo": "CX-5", "version": "Grand Touring", "anio": 2026,
        "tipo": "SUV", "precio": Decimal("42000.00"), "moneda": Moneda.DOLARES,
        "descripcion": "SUV premium con acabados de alta gama.",
        "url_imagen": (
            "https://acnews.blob.core.windows.net/imgnews/medium/"
            "NAZ_de411291377343648e73fbe7dcd94da4.webp"
        ),
    },
]


def _crear_usuarios(sesion: Session) -> tuple[Usuario, Usuario]:
    """Crea los usuarios de prueba y devuelve (demo, maria)."""

    demo = Usuario(
        nombre="Usuario",
        apellido="Demo",
        correo="demo@autofacil.local",
        usuario="demo",
        password_hash=hashear_password("Demo1234"),
        activo=True,
    )
    maria = Usuario(
        nombre="Maria",
        apellido="Perez",
        correo="maria@autofacil.local",
        usuario="maria",
        password_hash=hashear_password("Maria1234"),
        activo=True,
    )
    sesion.add_all([demo, maria])
    sesion.flush()
    return demo, maria


def _crear_vehiculos(sesion: Session, usuario_id: int) -> None:
    """Crea los vehiculos de ejemplo del usuario indicado."""

    sesion.add_all([Vehiculo(usuario_id=usuario_id, **fila) for fila in _VEHICULOS])


def _crear_simulacion_demo(sesion: Session, usuario: Usuario) -> None:
    """Crea una simulacion de Compra Inteligente de ejemplo para el usuario."""

    vehiculo = (
        sesion.query(Vehiculo)
        .filter(Vehiculo.usuario_id == usuario.id, Vehiculo.moneda == Moneda.SOLES)
        .first()
    )
    if vehiculo is None:
        return

    solicitud = SimulacionGuardarRequest(
        vehiculo_id=vehiculo.id,
        nombre="Compra Inteligente - demostracion",
        moneda=vehiculo.moneda,
        plan=Plan.PLAN_36,
        porcentaje_cuota_inicial=Decimal("0.20"),
        tipo_tasa=TipoTasa.NOMINAL,
        valor_tasa=Decimal("0.15"),
        capitalizacion=Capitalizacion.DIARIA,
        meses_gracia_total=3,
        meses_gracia_parcial=3,
        costo_notarial=Decimal("100"),
        costo_registral=Decimal("75"),
        gps_periodico=Decimal("20"),
        portes_periodico=Decimal("3.5"),
        gastos_adm_periodico=Decimal("3.5"),
        seguro_desgravamen_mensual=Decimal("0.00049"),
        seguro_riesgo_anual=Decimal("0.003"),
        cok_anual=Decimal("0.50"),
        fecha_inicio=date(2026, 1, 1),
    )
    resultado = calcular_desde_solicitud(solicitud, vehiculo)
    simulacion = Simulacion(
        codigo="PENDIENTE",
        vehiculo_id=vehiculo.id,
        usuario_id=usuario.id,
        estado=EstadoSimulacion.CALCULADA,
    )
    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    sesion.add(simulacion)
    sesion.flush()
    simulacion.codigo = f"SIM-{simulacion.id:06d}"
    simulacion.cronograma = construir_filas_cronograma(resultado)


def sembrar_datos(sesion: Session) -> bool:
    """Inserta los datos semilla que falten. Devuelve True si inserto algo."""

    creado = False

    demo = sesion.query(Usuario).filter(Usuario.usuario == "demo").first()
    maria = sesion.query(Usuario).filter(Usuario.usuario == "maria").first()
    if sesion.query(Usuario).first() is None:
        demo, maria = _crear_usuarios(sesion)
        creado = True

    if demo is not None and maria is not None and sesion.query(Vehiculo).first() is None:
        _crear_vehiculos(sesion, demo.id)
        _crear_vehiculos(sesion, maria.id)
        sesion.flush()
        _crear_simulacion_demo(sesion, demo)
        creado = True

    if creado:
        sesion.commit()
    return creado


def ejecutar_semilla() -> None:
    """Punto de entrada para sembrar datos desde la linea de comandos."""

    crear_tablas()
    sesion = FabricaSesion()
    try:
        if sembrar_datos(sesion):
            print("Datos semilla creados correctamente.")
        else:
            print("La base de datos ya contiene datos; no se realizaron cambios.")
    finally:
        sesion.close()


if __name__ == "__main__":
    ejecutar_semilla()
