"""Punto de entrada de la aplicacion FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import obtener_configuracion
from app.database import FabricaSesion, crear_tablas
from app.rutas import (
    auth,
    clientes,
    perfil,
    simulaciones,
    tipo_cambio,
    vehiculos,
)

configuracion = obtener_configuracion()

# Grupos de endpoints en Swagger.
ETIQUETAS_OPENAPI = [
    {
        "name": "Autenticacion",
        "description": (
            "Registro e inicio de sesion del asesor. El login (`/auth/login-json`) y el "
            "registro (`/auth/registro`) devuelven un token JWT de acceso que debe enviarse "
            "como `Authorization: Bearer <token>` en el resto de endpoints."
        ),
    },
    {
        "name": "Perfil",
        "description": (
            "Consulta y actualizacion del perfil del propio usuario (nombre, correo, "
            "usuario y contrasena). Cambiar el usuario no invalida la sesion."
        ),
    },
    {
        "name": "Clientes",
        "description": (
            "Gestion de la cartera de clientes del asesor: alta, busqueda, edicion y baja "
            "logica. Cada asesor solo ve y opera sus propios clientes."
        ),
    },
    {
        "name": "Vehiculos",
        "description": (
            "Catalogo de vehiculos del asesor: alta, busqueda, edicion y baja logica. El "
            "vehiculo solo maneja el indicador `activo` (no tiene estado comercial)."
        ),
    },
    {
        "name": "Simulaciones",
        "description": (
            "Nucleo de AutoFacil: previsualizacion (`/calcular`), guardado, listado con "
            "filtros, detalle (con el cronograma de la cuota regular y del cuoton), edicion "
            "con recalculo, recalculo y archivado (baja logica) de las propuestas de credito "
            "vehicular Compra Inteligente."
        ),
    },
    {
        "name": "Tipo de cambio",
        "description": (
            "Consulta del tipo de cambio referencial USD/PEN en tiempo real desde una API "
            "publica (con respaldo local). Es informativo y no altera el calculo financiero."
        ),
    },
]

DESCRIPCION_API = """
API del sistema **AutoFacil**: simulacion y gestion de credito vehicular para una
entidad financiera en Peru. Cada asesor trabaja de forma aislada sobre su propia
cartera de clientes, su catalogo de vehiculos y sus simulaciones.

### Producto

Producto **Compra Inteligente** (estilo Interbank, Peru): metodo frances vencido
ordinario con meses comerciales de 30 dias (NDxA = 360). El precio se reparte en
cuota inicial, cuotas mensuales y un **cuoton** (cuota final) que se difiere y se
paga integro en el periodo **N+1**. El **plan** define el numero de cuotas y el
cuoton: Plan 24 -> 24 cuotas y 50%; Plan 36 -> 36 cuotas y 40%. La tasa es fija
(efectiva o nominal; si es nominal la capitalizacion es diaria o mensual). Los
calculos usan aritmetica decimal de alta precision y no redondean valores
intermedios.

### Autenticacion

1. Cree una cuenta en `POST /auth/registro` o use una cuenta de prueba (`demo` /
   `Demo1234`).
2. Obtenga el token con `POST /auth/login-json` (o el formulario `POST /auth/login`).
3. Pulse **Authorize** arriba a la derecha y pegue el token para autorizar las
   llamadas a los endpoints protegidos.

### Convenciones

* Las tasas y porcentajes viajan en **formato decimal**: `0.18` = 18%, `0.20` =
  20% de cuota inicial.
* Los importes monetarios se devuelven como numeros (`float`); el frontend aplica
  el formato de moneda.
* La baja de clientes, vehiculos y simulaciones es **logica** (no hay borrado
  fisico): `DELETE` desactiva/archiva conservando el historial.
"""


@asynccontextmanager
async def ciclo_vida(_: FastAPI):
    """Inicializa la base de datos y los datos semilla al arrancar el servicio."""

    crear_tablas()
    from app.datos_semilla import sembrar_datos

    sesion = FabricaSesion()
    try:
        sembrar_datos(sesion)
    finally:
        sesion.close()
    yield


aplicacion = FastAPI(
    title="AutoFacil API",
    description=DESCRIPCION_API,
    version=configuracion.version_aplicacion,
    openapi_tags=ETIQUETAS_OPENAPI,
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=ciclo_vida,
)

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=configuracion.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

aplicacion.include_router(auth.enrutador)
aplicacion.include_router(perfil.enrutador)
aplicacion.include_router(clientes.enrutador)
aplicacion.include_router(vehiculos.enrutador)
aplicacion.include_router(simulaciones.enrutador)
aplicacion.include_router(tipo_cambio.enrutador)


@aplicacion.get("/", tags=["Estado"], summary="Estado del servicio")
def estado_servicio() -> dict:
    """Endpoint de verificacion del estado del servicio."""

    return {
        "aplicacion": configuracion.nombre_aplicacion,
        "version": configuracion.version_aplicacion,
        "estado": "activo",
    }


# Alias ASGI estandar para uvicorn (app.main:app).
app = aplicacion
