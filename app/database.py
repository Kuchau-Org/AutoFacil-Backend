"""Motor, sesion y base declarativa de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion

configuracion = obtener_configuracion()

argumentos_conexion = (
    {"check_same_thread": False}
    if configuracion.url_base_datos.startswith("sqlite")
    else {}
)

motor = create_engine(
    configuracion.url_base_datos,
    connect_args=argumentos_conexion,
    echo=False,
)


# Activa las claves foraneas en SQLite (para el borrado en cascada).
if configuracion.url_base_datos.startswith("sqlite"):

    @event.listens_for(motor, "connect")
    def _activar_foreign_keys(conexion, _registro):  # noqa: ANN001
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


FabricaSesion = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredan todos los modelos ORM."""


def obtener_sesion() -> Generator[Session, None, None]:
    """Provee una sesion de base de datos y garantiza su cierre posterior."""

    sesion = FabricaSesion()
    try:
        yield sesion
    finally:
        sesion.close()


def crear_tablas() -> None:
    """Crea las tablas declaradas que aun no existan."""

    from app import modelos  # noqa: F401

    Base.metadata.create_all(bind=motor)
