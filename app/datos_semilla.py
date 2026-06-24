"""Datos semilla para ejecucion local (idempotente)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import FabricaSesion, crear_tablas
from app.esquemas.simulacion import SimulacionGuardarRequest
from app.modelos.cliente import Cliente
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


# Catalogo de vehiculos de ejemplo (cada asesor recibe su propia copia).
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

# Clientes de ejemplo por asesor (cada asesor ve solo los suyos).
_CLIENTES_DEMO = [
    {
        "tipo_documento": "DNI", "numero_documento": "76543821",
        "nombres": "Carlos Alberto", "apellidos": "Mendez Rivas",
        "correo": "carlos.mendez@correo.local", "telefono": "987321654",
        "direccion": "Av. Javier Prado 123, Lima", "fecha_nacimiento": date(1990, 5, 14),
        "ingreso_mensual": Decimal("8500.00"), "gastos_mensuales": Decimal("3000.00"),
        "otras_deudas": Decimal("800.00"), "moneda_ingresos": Moneda.SOLES,
    },
    {
        "tipo_documento": "DNI", "numero_documento": "72914583",
        "nombres": "Andrea", "apellidos": "Salazar Paredes",
        "correo": "andrea.salazar@correo.local", "telefono": "912345876",
        "direccion": "Calle Los Pinos 456, Arequipa", "fecha_nacimiento": date(1988, 11, 2),
        "ingreso_mensual": Decimal("9800.00"), "gastos_mensuales": Decimal("3500.00"),
        "otras_deudas": Decimal("1200.00"), "moneda_ingresos": Moneda.DOLARES,
    },
]
_CLIENTES_MARIA = [
    {
        "tipo_documento": "DNI", "numero_documento": "44556677",
        "nombres": "Lucia", "apellidos": "Garcia Torres",
        "correo": "lucia.garcia@correo.local", "telefono": "999888777",
        "direccion": "Jr. Union 789, Trujillo", "fecha_nacimiento": date(1993, 3, 28),
        "ingreso_mensual": Decimal("6200.00"), "gastos_mensuales": Decimal("2100.00"),
        "otras_deudas": Decimal("0.00"), "moneda_ingresos": Moneda.SOLES,
    },
]


def _crear_usuarios(sesion: Session) -> tuple[Usuario, Usuario]:
    """Crea los asesores de prueba y devuelve (demo, maria)."""

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


def _crear_clientes(sesion: Session, usuario_id: int, datos: list[dict]) -> None:
    """Inserta los clientes indicados como propiedad del asesor."""

    sesion.add_all([Cliente(usuario_id=usuario_id, **fila) for fila in datos])


def _crear_vehiculos(sesion: Session, usuario_id: int) -> None:
    """Crea el catalogo de vehiculos de ejemplo del asesor indicado."""

    sesion.add_all(
        [Vehiculo(usuario_id=usuario_id, **fila) for fila in _VEHICULOS]
    )


def _crear_simulacion_demo(sesion: Session, usuario: Usuario) -> None:
    """Crea una simulacion de Compra Inteligente (con cuota balon) para el asesor."""

    cliente = sesion.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
    vehiculo = (
        sesion.query(Vehiculo)
        .filter(Vehiculo.usuario_id == usuario.id, Vehiculo.moneda == Moneda.SOLES)
        .first()
    )
    if cliente is None or vehiculo is None:
        return

    solicitud = SimulacionGuardarRequest(
        cliente_id=cliente.id,
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
        cliente_id=cliente.id,
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
    """Inserta los datos semilla que falten (idempotente).

    Devuelve True si se inserto algo y False si nada cambio.
    """

    creado = False

    demo = sesion.query(Usuario).filter(Usuario.usuario == "demo").first()
    maria = sesion.query(Usuario).filter(Usuario.usuario == "maria").first()
    if sesion.query(Usuario).first() is None:
        demo, maria = _crear_usuarios(sesion)
        creado = True

    if demo is not None and maria is not None and sesion.query(Cliente).first() is None:
        _crear_clientes(sesion, demo.id, _CLIENTES_DEMO)
        _crear_clientes(sesion, maria.id, _CLIENTES_MARIA)
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
