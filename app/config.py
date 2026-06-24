"""Configuracion de la aplicacion leida del entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta de la base SQLite (anclada al directorio del backend).
DIRECTORIO_BACKEND = Path(__file__).resolve().parent.parent
RUTA_BASE_DATOS = (DIRECTORIO_BACKEND / "autofacil.db").as_posix()


class Configuracion(BaseSettings):
    """Parametros de configuracion."""

    nombre_aplicacion: str = "AutoFacil"
    descripcion_aplicacion: str = (
        "Sistema de simulacion y gestion de credito vehicular para una entidad "
        "financiera en Peru."
    )
    version_aplicacion: str = "1.0.0"

    url_base_datos: str = f"sqlite:///{RUTA_BASE_DATOS}"

    # En produccion definir AUTOFACIL_CLAVE_SECRETA en el entorno.
    clave_secreta: str = "autofacil-clave-secreta-solo-desarrollo-local-cambiar"
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_token: int = 60 * 8

    origenes_cors: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    precision_decimal: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTOFACIL_")


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve una instancia unica y cacheada de la configuracion."""

    return Configuracion()
