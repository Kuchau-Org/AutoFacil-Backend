"""Punto de entrada de la aplicacion FastAPI de AutoFacil.

Configura la aplicacion, el middleware CORS para el desarrollo local, registra
los enrutadores, organiza la documentacion Swagger y crea las tablas y los
datos semilla al iniciar.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import obtener_configuracion
from app.database import FabricaSesion, crear_tablas
from app.rutas import (
    auditoria,
    auth,
    clientes,
    indicadores,
    perfil,
    publico,
    simulaciones,
    tipo_cambio,
    vehiculos,
)

configuracion = obtener_configuracion()

# Metadatos de los grupos de endpoints mostrados en Swagger.
ETIQUETAS_OPENAPI = [
    {
        "name": "Autenticacion",
        "description": "Registro e inicio de sesion. El login y el registro devuelven un token "
        "JWT que debe enviarse como Bearer.",
    },
    {"name": "Perfil", "description": "Consulta y actualizacion del perfil del propio usuario."},
    {"name": "Clientes", "description": "Registro y gestion de los clientes del asesor."},
    {"name": "Vehiculos", "description": "Catalogo de vehiculos del asesor."},
    {
        "name": "Simulaciones",
        "description": "Calculo, guardado, edicion, recalculo, cambio de estado y eliminacion "
        "de las simulaciones de credito vehicular de la entidad.",
    },
    {
        "name": "Cronograma de pagos",
        "description": "Consulta del cronograma de pagos detallado de una simulacion.",
    },
    {
        "name": "Indicadores financieros",
        "description": "Indicadores agregados para el panel principal (totales, TCEA promedio).",
    },
    {
        "name": "Tipo de cambio",
        "description": "Consulta del tipo de cambio referencial en tiempo real desde una API publica.",
    },
    {
        "name": "Auditoria",
        "description": "Registro de creacion, edicion y recalculo de las operaciones del usuario.",
    },
    {
        "name": "Vista del cliente",
        "description": "Consulta publica de solo lectura de una simulacion mediante su enlace compartible.",
    },
]

DESCRIPCION_API = """
API del sistema **AutoFacil** para la simulacion y gestion de credito vehicular
para una entidad financiera en Peru.

Implementa el metodo frances vencido ordinario con meses comerciales de 30 dias.
Los calculos financieros usan aritmetica decimal de alta precision y no redondean
valores intermedios.

Autenticacion: use el endpoint de login para obtener un token JWT (tipo
"acceso") y pulse el boton **Authorize** para autorizar las llamadas a los
endpoints protegidos.

Las tasas y porcentajes se expresan en formato decimal (0.18 = 18%).
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
aplicacion.include_router(indicadores.enrutador)
aplicacion.include_router(tipo_cambio.enrutador)
aplicacion.include_router(auditoria.enrutador)
aplicacion.include_router(publico.enrutador)


@aplicacion.get("/", tags=["Estado"], summary="Estado del servicio")
def estado_servicio() -> dict:
    """Endpoint de verificacion del estado del servicio."""

    return {
        "aplicacion": configuracion.nombre_aplicacion,
        "version": configuracion.version_aplicacion,
        "estado": "activo",
    }


# Alias `app`: punto de entrada ASGI estandar esperado por uvicorn al ejecutar
# `uvicorn app.main:app`. Apunta a la misma instancia que `aplicacion`.
app = aplicacion
