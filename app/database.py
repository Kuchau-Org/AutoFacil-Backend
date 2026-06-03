"""Configuracion del motor de base de datos y de la sesion de SQLAlchemy.

Expone la fabrica de sesiones, la clase base declarativa y la dependencia
`obtener_sesion` utilizada por las rutas de FastAPI.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion

configuracion = obtener_configuracion()

# `check_same_thread` solo aplica a SQLite y permite usar la conexion en el
# contexto multihilo del servidor de desarrollo.
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


# SQLite no aplica las claves foraneas por defecto; se activan en cada conexion
# para que el borrado en cascada del cronograma funcione correctamente.
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
    """Crea todas las tablas declaradas si aun no existen en la base de datos."""

    # La importacion local asegura que todos los modelos esten registrados en
    # el metadata antes de crear las tablas.
    from app import modelos  # noqa: F401
    from app.migraciones import aplicar_migraciones

    Base.metadata.create_all(bind=motor)
    # Ajusta una base SQLite anterior agregando columnas nuevas y normalizando
    # estados; en una base recien creada no realiza cambios.
    aplicar_migraciones(motor)
