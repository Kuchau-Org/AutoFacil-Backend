"""Configuracion central de la aplicacion AutoFacil.

Carga los parametros de ejecucion desde variables de entorno con valores por
defecto adecuados para ejecucion local. No contiene ninguna configuracion de
despliegue.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Directorio raiz del backend (carpeta que contiene el paquete `app`). Se usa
# para anclar la base de datos a una ruta absoluta y que no dependa del
# directorio desde el que se ejecute uvicorn.
DIRECTORIO_BACKEND = Path(__file__).resolve().parent.parent
RUTA_BASE_DATOS = (DIRECTORIO_BACKEND / "autofacil.db").as_posix()


class Configuracion(BaseSettings):
    """Parametros de configuracion leidos del entorno o de valores por defecto."""

    nombre_aplicacion: str = "AutoFacil"
    descripcion_aplicacion: str = (
        "Sistema de simulacion y gestion de credito vehicular para una entidad "
        "financiera en Peru."
    )
    version_aplicacion: str = "1.0.0"

    # Cadena de conexion a la base de datos local (SQLite con ruta absoluta).
    # La ruta absoluta evita que se cree una base vacia distinta segun el
    # directorio de arranque, que era una causa de fallos de login.
    url_base_datos: str = f"sqlite:///{RUTA_BASE_DATOS}"

    # Parametros de seguridad para la firma de tokens JWT.
    # En produccion DEBE definirse AUTOFACIL_CLAVE_SECRETA en el entorno (.env).
    # Este valor por defecto solo es valido para ejecucion local de desarrollo.
    clave_secreta: str = "autofacil-clave-secreta-solo-desarrollo-local-cambiar"
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_token: int = 60 * 8

    # Dias de validez del enlace publico compartible con el cliente.
    dias_expiracion_token_compartir: int = 30

    # Origenes permitidos para CORS durante el desarrollo local.
    origenes_cors: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Precision decimal global utilizada en los calculos financieros.
    precision_decimal: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTOFACIL_")


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve una instancia unica y cacheada de la configuracion."""

    return Configuracion()
