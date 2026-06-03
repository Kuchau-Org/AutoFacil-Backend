"""Migraciones ligeras para una base de datos SQLite ya existente.

Que problema resuelve este archivo
-----------------------------------
Al iniciar, la aplicacion crea las tablas con `create_all`. Ese metodo crea las
tablas que faltan, pero NO modifica una tabla que ya existe. Por eso, si alguien
ya tenia una base de datos creada con una version anterior de AutoFacil, al
actualizar el codigo esa base se quedaria con la estructura vieja (le faltarian
columnas nuevas o tendria columnas que ya no se usan).

Para no obligar a borrar la base y perder los datos, aqui se hacen tres ajustes
sobre la base existente:

1. Se AGREGAN las columnas nuevas que el modelo actual necesita y que la base
   vieja no tiene. Se crean con un valor por defecto razonable para que las filas
   antiguas sigan siendo validas.
2. Se ELIMINAN las columnas que versiones anteriores creaban pero que el modelo
   actual ya no usa. Esto importa porque algunas eran obligatorias (NOT NULL) sin
   valor por defecto y, de quedarse, romperian los INSERT nuevos.
3. Se NORMALIZAN los estados de simulacion antiguos al esquema actual, que solo
   tiene dos: CALCULADA (vigente) y ARCHIVADA (dada de baja, pero conservada).

Todo es idempotente: en una base recien creada no falta ninguna columna, no hay
columnas obsoletas ni estados antiguos, asi que esta funcion no cambia nada.
"""

from sqlalchemy import Engine, text

# Columnas que el modelo actual SI usa pero que una base anterior podria no tener.
# Para cada una se indica su definicion en SQLite (tipo + valor por defecto). El
# valor por defecto se elige para que las filas viejas conserven su sentido (por
# ejemplo, un cargo que antes no existia se asume en 0).
_COLUMNAS_A_AGREGAR = {
    "simulaciones": {
        "porcentaje_cuota_final": "NUMERIC NOT NULL DEFAULT 0",
        "cuota_final": "NUMERIC NOT NULL DEFAULT 0",
        "desgravamen_consentido": "BOOLEAN NOT NULL DEFAULT 0",
        "gps_instalacion": "NUMERIC NOT NULL DEFAULT 0",
        "gps_mantenimiento_mensual": "NUMERIC NOT NULL DEFAULT 0",
        "gps_reposicion": "NUMERIC NOT NULL DEFAULT 0",
        "gastos_notariales": "NUMERIC NOT NULL DEFAULT 0",
        "gastos_registrales": "NUMERIC NOT NULL DEFAULT 0",
        "tasacion": "NUMERIC NOT NULL DEFAULT 0",
        "gastos_iniciales": "NUMERIC NOT NULL DEFAULT 0",
        "tasa_descuento_van": "NUMERIC NOT NULL DEFAULT 0",
        "tasa_moratoria_anual": "NUMERIC NOT NULL DEFAULT 0",
        "aseguradora": "VARCHAR",
        "numero_poliza": "VARCHAR",
        "coberturas": "VARCHAR",
        "total_cargos_desembolso": "NUMERIC NOT NULL DEFAULT 0",
        "total_gps_mantenimiento": "NUMERIC NOT NULL DEFAULT 0",
    },
    "cronogramas_pago": {
        "gps_mantenimiento": "NUMERIC NOT NULL DEFAULT 0",
        "cuota_final_extraordinaria": "NUMERIC NOT NULL DEFAULT 0",
    },
}

# Columnas que crearon versiones ANTERIORES de la app y que el modelo actual ya
# NO tiene. Se listan por su nombre antiguo (no son campos vigentes: aparecen aqui
# solo para poder borrarlos de una base vieja). Por ejemplo, antes cada gasto
# tenia una "modalidad" de pago y el GPS un "pagado_por"; eso se simplifico y se
# quito. Tambien el vehiculo tenia un estado comercial que se elimino: ahora solo
# existe `activo` (baja logica). Se eliminan con ALTER TABLE DROP COLUMN.
_COLUMNAS_A_ELIMINAR = {
    "simulaciones": (
        "total_gastos",
        "tasa_fija",
        "comision_mensual",
        "total_comisiones",
        "total_pagos_directos",
        "cargo_prenda",
        "cargo_prenda_modalidad",
        "gastos_notariales_modalidad",
        "gastos_registrales_modalidad",
        "tasacion_modalidad",
        "seguro_vehicular_modalidad",
        "gps_pagado_por",
    ),
    "cronogramas_pago": ("comision",),
    "vehiculos": ("estado",),
}

# Estados de simulacion de versiones anteriores y su equivalente actual. El
# esquema vigente solo tiene CALCULADA y ARCHIVADA, asi que los estados viejos se
# reasignan: los que implicaban una baja (anulada/rechazada) pasan a ARCHIVADA y
# el resto (borrador/aprobada) a CALCULADA.
_ESTADOS_A_ARCHIVADA = ("ANULADA", "RECHAZADA")
_ESTADOS_A_CALCULADA = ("BORRADOR", "APROBADA")


def _tablas_existentes(conexion) -> set[str]:
    """Devuelve los nombres de las tablas que existen en la base SQLite."""

    filas = conexion.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {fila[0] for fila in filas}


def _columnas_de(conexion, tabla: str) -> set[str]:
    """Devuelve los nombres de las columnas de una tabla (via PRAGMA de SQLite)."""

    filas = conexion.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
    # En el resultado de PRAGMA table_info, el indice 1 de cada fila es el nombre.
    return {fila[1] for fila in filas}


def aplicar_migraciones(engine: Engine) -> None:
    """Acomoda una base SQLite previa al esquema actual (agrega/elimina columnas
    y normaliza estados). En una base nueva no hace ningun cambio."""

    # Solo aplica a SQLite (la base local del proyecto). En otros motores no hace
    # nada para evitar ejecutar SQL especifico de SQLite.
    if engine.dialect.name != "sqlite":
        return

    # `engine.begin()` abre una transaccion: si algo falla, no se aplica nada.
    with engine.begin() as conexion:
        tablas = _tablas_existentes(conexion)

        # 1) Agrega las columnas nuevas que falten en cada tabla.
        for tabla, columnas in _COLUMNAS_A_AGREGAR.items():
            if tabla not in tablas:
                continue
            existentes = _columnas_de(conexion, tabla)
            for columna, definicion in columnas.items():
                if columna not in existentes:
                    conexion.execute(
                        text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
                    )

        # 2) Elimina las columnas obsoletas que podrian impedir los INSERT nuevos.
        for tabla, columnas in _COLUMNAS_A_ELIMINAR.items():
            if tabla not in tablas:
                continue
            existentes = _columnas_de(conexion, tabla)
            for columna in columnas:
                if columna in existentes:
                    try:
                        conexion.execute(
                            text(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
                        )
                    except Exception:
                        # Las versiones de SQLite anteriores a la 3.35 (2021) no
                        # soportan DROP COLUMN. En ese caso la columna se queda,
                        # pero sin uso: no afecta el funcionamiento de la app.
                        pass

        # 3) Reasigna los estados de simulacion antiguos al esquema actual.
        if "simulaciones" in tablas:
            estados_archivada = ", ".join(f"'{e}'" for e in _ESTADOS_A_ARCHIVADA)
            estados_calculada = ", ".join(f"'{e}'" for e in _ESTADOS_A_CALCULADA)
            conexion.execute(
                text(
                    f"UPDATE simulaciones SET estado='ARCHIVADA' "
                    f"WHERE estado IN ({estados_archivada})"
                )
            )
            conexion.execute(
                text(
                    f"UPDATE simulaciones SET estado='CALCULADA' "
                    f"WHERE estado IN ({estados_calculada})"
                )
            )
