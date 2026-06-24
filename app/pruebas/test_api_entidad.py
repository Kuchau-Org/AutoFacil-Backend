"""Pruebas de API con una base de datos aislada.

Usa un motor SQLite temporal y sobreescribe la dependencia de sesion para no
tocar la base de datos de desarrollo. Cubre autenticacion, aislamiento de datos
por asesor (cada uno ve solo lo suyo), validaciones de negocio, dashboard por
moneda, tipo de cambio y el credito frances con y sin cuota balon.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, obtener_sesion
from app.main import app
from app.modelos.cliente import Cliente
from app.modelos.enumeraciones import Moneda
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.hash import hashear_password

_RUTA = os.path.join(tempfile.gettempdir(), "_autofacil_pytest_api.db")
_motor = create_engine(f"sqlite:///{_RUTA}", connect_args={"check_same_thread": False})
SesionPrueba = sessionmaker(bind=_motor, autoflush=False, autocommit=False)


def _sesion_override():
    sesion = SesionPrueba()
    try:
        yield sesion
    finally:
        sesion.close()


app.dependency_overrides[obtener_sesion] = _sesion_override
cliente = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def preparar_datos():
    """Crea el esquema y dos asesores con datos propios y aislados."""

    Base.metadata.drop_all(_motor)
    Base.metadata.create_all(_motor)
    sesion = SesionPrueba()
    asesor = Usuario(
        nombre="Asesor", apellido="Uno", correo="asesor@autofacil.local",
        usuario="asesor", password_hash=hashear_password("Asesor123"), activo=True,
    )
    otro = Usuario(
        nombre="Asesor", apellido="Dos", correo="asesor2@autofacil.local",
        usuario="asesor2", password_hash=hashear_password("Asesor456"), activo=True,
    )
    sesion.add_all([asesor, otro])
    sesion.flush()
    sesion.add_all(
        [
            # Datos del asesor 1.
            Cliente(usuario_id=asesor.id, numero_documento="11111111", nombres="Ana",
                    apellidos="Activa", ingreso_mensual=8000, gastos_mensuales=2000,
                    otras_deudas=500, moneda_ingresos=Moneda.SOLES, activo=True),
            Cliente(usuario_id=asesor.id, numero_documento="22222222", nombres="Ines",
                    apellidos="Inactiva", moneda_ingresos=Moneda.SOLES, activo=False),
            Vehiculo(usuario_id=asesor.id, marca="Toyota", modelo="Yaris", anio=2026,
                     precio=80000, moneda=Moneda.SOLES, activo=True),
            Vehiculo(usuario_id=asesor.id, marca="Hyundai", modelo="Tucson", anio=2026,
                     precio=35000, moneda=Moneda.DOLARES, activo=True),
            Vehiculo(usuario_id=asesor.id, marca="Kia", modelo="Rio", anio=2024,
                     precio=60000, moneda=Moneda.SOLES, activo=False),
            # Datos del asesor 2 (no deben verse desde el asesor 1).
            Cliente(usuario_id=otro.id, numero_documento="99999999", nombres="Beto",
                    apellidos="Otro", ingreso_mensual=5000, moneda_ingresos=Moneda.SOLES,
                    activo=True),
            Vehiculo(usuario_id=otro.id, marca="Ford", modelo="Ranger", anio=2026,
                     precio=120000, moneda=Moneda.SOLES, activo=True),
        ]
    )
    sesion.commit()
    sesion.close()
    yield
    app.dependency_overrides.clear()
    _motor.dispose()
    if os.path.exists(_RUTA):
        os.remove(_RUTA)


def _token(usuario: str, password: str) -> str:
    return cliente.post(
        "/auth/login-json", json={"usuario": usuario, "password": password}
    ).json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token('asesor', 'Asesor123')}"}


def _headers2() -> dict:
    return {"Authorization": f"Bearer {_token('asesor2', 'Asesor456')}"}


def _ids():
    h = _headers()
    cli = cliente.get("/clientes", params={"incluir_inactivos": True}, headers=h).json()
    veh = cliente.get("/vehiculos", params={"incluir_inactivos": True}, headers=h).json()
    return h, cli, veh


def _veh_pen(veh):
    return next(v for v in veh if v["moneda"] == "PEN" and v["activo"])


def _solicitud_base(cliente_id, vehiculo_id, moneda="PEN", **extra):
    base = {
        "cliente_id": cliente_id, "vehiculo_id": vehiculo_id, "moneda": moneda,
        "plan": "PLAN_36", "tipo_tasa": "EFECTIVA", "valor_tasa": 0.15,
        "porcentaje_cuota_inicial": 0.2, "cok_anual": 0.10,
    }
    base.update(extra)
    return base


def _crear_sim(h, cli, veh, **extra):
    activo = next(c for c in cli if c["activo"])
    return cliente.post(
        "/simulaciones",
        json={**_solicitud_base(activo["id"], _veh_pen(veh)["id"], **extra), "estado": "CALCULADA"},
        headers=h,
    )


def test_moneda_incompatible_rechazada():
    """Un credito PEN sobre un vehiculo USD debe rechazarse."""

    h, cli, veh = _ids()
    activo = next(c for c in cli if c["activo"])
    veh_usd = next(v for v in veh if v["moneda"] == "USD")
    r = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(activo["id"], veh_usd["id"], moneda="PEN"),
        headers=h,
    )
    assert r.status_code == 400
    assert "moneda" in r.json()["detail"].lower()


def test_crear_con_vehiculo_inactivo_rechazado():
    """No se puede GUARDAR una nueva simulacion con un vehiculo dado de baja."""

    h, cli, veh = _ids()
    activo = next(c for c in cli if c["activo"])
    inactivo = next(v for v in veh if not v["activo"])
    r = cliente.post(
        "/simulaciones",
        json={**_solicitud_base(activo["id"], inactivo["id"]), "estado": "CALCULADA"},
        headers=h,
    )
    assert r.status_code == 400


def test_crear_con_cliente_inactivo_rechazado():
    """No se puede GUARDAR una nueva simulacion con un cliente inactivo."""

    h, cli, veh = _ids()
    inactivo = next(c for c in cli if not c["activo"])
    r = cliente.post(
        "/simulaciones",
        json={**_solicitud_base(inactivo["id"], _veh_pen(veh)["id"]), "estado": "CALCULADA"},
        headers=h,
    )
    assert r.status_code == 400


def test_cualquier_vehiculo_activo_se_puede_simular():
    """Todo vehiculo activo del asesor se puede simular (no hay estado comercial)."""

    h, cli, veh = _ids()
    activo = next(c for c in cli if c["activo"])
    activos = [v for v in veh if v["activo"]]
    assert activos, "Deberia haber vehiculos activos para simular."
    for objetivo in activos:
        r = cliente.post(
            "/simulaciones/calcular",
            json=_solicitud_base(
                activo["id"], objetivo["id"], moneda=objetivo["moneda"], tipo_cambio_referencial=3.8
            ),
            headers=h,
        )
        assert r.status_code == 200, r.text


def test_planes_difieren_la_cuota_final_y_cierran_en_cero():
    """Producto Compra Inteligente: ambos planes difieren el cuoton al periodo N+1."""

    h, cli, veh = _ids()
    activo = next(c for c in cli if c["activo"])
    veh_pen = _veh_pen(veh)["id"]

    plan36 = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(activo["id"], veh_pen, plan="PLAN_36"),
        headers=h,
    ).json()
    plan24 = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(activo["id"], veh_pen, plan="PLAN_24"),
        headers=h,
    ).json()

    # El cuoton es 40% (Plan 36) y 50% (Plan 24) del precio.
    assert plan36["porcentaje_cuota_final"] == 0.40
    assert plan24["porcentaje_cuota_final"] == 0.50
    # El cronograma tiene N+1 filas y el cuoton se paga en la ultima.
    assert len(plan36["cronograma"]) == 37 and len(plan24["cronograma"]) == 25
    for res in (plan36, plan24):
        ultima = res["cronograma"][-1]
        assert ultima["tipo_periodo"] == "CUOTA_FINAL"
        assert ultima["amortizacion_cuoton"] > 0
        assert abs(ultima["saldo_final_cuoton"]) < 0.01
        assert abs(ultima["saldo_final"]) < 0.01


def test_simulacion_valida_saldo_cero_e_indicadores():
    """Una simulacion valida termina en saldo cero y trae VAN, TIR, TCEA y tasa VAN."""

    h, cli, veh = _ids()
    r = _crear_sim(h, cli, veh)
    assert r.status_code == 201
    sim = r.json()
    assert abs(sim["cronograma"][-1]["saldo_final_cuoton"]) < 0.01
    assert sim["van"] is not None and sim["tir_mensual"] is not None and sim["tcea"] is not None
    assert "saldo_financiado" in sim


def test_aislamiento_por_asesor():
    """Cada asesor solo ve sus clientes, vehiculos y simulaciones."""

    h1, cli, veh = _ids()
    # El asesor 1 no ve al cliente "Beto" ni al "Ford Ranger" del asesor 2.
    assert all(c["nombres"] != "Beto" for c in cli)
    assert all(v["marca"] != "Ford" for v in veh)

    # El asesor 1 crea una simulacion.
    sim = _crear_sim(h1, cli, veh).json()

    # El asesor 2 no la ve en su historial ni puede abrirla.
    h2 = _headers2()
    lista2 = cliente.get("/simulaciones", headers=h2).json()
    assert all(s["id"] != sim["id"] for s in lista2)
    assert cliente.get(f"/simulaciones/{sim['id']}", headers=h2).status_code == 404
    # Ni archivarla.
    assert cliente.delete(f"/simulaciones/{sim['id']}", headers=h2).status_code == 404
    # El propio dueno si puede archivarla (baja logica).
    archivada = cliente.delete(f"/simulaciones/{sim['id']}", headers=h1)
    assert archivada.status_code == 200
    assert archivada.json()["estado"] == "ARCHIVADA"


def test_busqueda_historial_por_cliente_o_vehiculo():
    """La busqueda del historial encuentra por nombre de cliente o de vehiculo."""

    h, cli, veh = _ids()
    _crear_sim(h, cli, veh)
    por_vehiculo = cliente.get("/simulaciones", params={"busqueda": "Toyota"}, headers=h).json()
    assert len(por_vehiculo) >= 1
    por_cliente = cliente.get("/simulaciones", params={"busqueda": "Ana"}, headers=h).json()
    assert len(por_cliente) >= 1


def test_registro_correo_obligatorio_y_normalizado():
    """El registro rechaza correo vacio y normaliza el correo a minusculas."""

    vacio = cliente.post(
        "/auth/registro",
        json={"nombre": "A", "apellido": "B", "correo": "  ", "usuario": "sincorreo", "password": "Clave123"},
    )
    assert vacio.status_code == 422
    ok = cliente.post(
        "/auth/registro",
        json={"nombre": "Carla", "apellido": "Diaz", "correo": "Carla.DIAZ@Mail.com",
              "usuario": "cdiaz", "password": "Clave123"},
    )
    assert ok.status_code == 200
    login = cliente.post(
        "/auth/login-json", json={"usuario": "carla.diaz@mail.com", "password": "Clave123"}
    )
    assert login.status_code == 200


def test_registro_usuario_invalido():
    """Rechaza nombres de usuario solo numericos o con '@'."""

    numerico = cliente.post(
        "/auth/registro",
        json={"nombre": "N", "apellido": "U", "correo": "num@mail.com",
              "usuario": "12345", "password": "Clave123"},
    )
    assert numerico.status_code == 422
    con_arroba = cliente.post(
        "/auth/registro",
        json={"nombre": "N", "apellido": "U", "correo": "arroba@mail.com",
              "usuario": "otro@mail.com", "password": "Clave123"},
    )
    assert con_arroba.status_code == 422


def test_password_excede_72_bytes():
    """Una contrasena de mas de 72 bytes se rechaza con un error claro."""

    r = cliente.post(
        "/auth/registro",
        json={"nombre": "L", "apellido": "P", "correo": "larga@mail.com",
              "usuario": "larga", "password": "a" * 73},
    )
    assert r.status_code == 422


def test_tipo_cambio_par_invalido():
    """Un par de monedas no soportado devuelve 400 (no una tasa enganosa)."""

    h = _headers()
    r = cliente.get("/tipo-cambio", params={"base": "EUR", "destino": "PEN"}, headers=h)
    assert r.status_code == 400


def test_tipo_cambio_en_tiempo_real():
    """El endpoint de tipo de cambio devuelve una tasa positiva (con respaldo)."""

    h = _headers()
    r = cliente.get("/tipo-cambio", params={"base": "USD", "destino": "PEN"}, headers=h)
    assert r.status_code == 200
    assert r.json()["tasa"] > 0
    assert cliente.get("/tipo-cambio").status_code == 401


def test_put_vehiculo_no_puede_desactivar():
    """La edicion de un vehiculo no puede cambiar `activo` (baja solo via DELETE)."""

    h, _, veh = _ids()
    objetivo = _veh_pen(veh)
    r = cliente.put(
        f"/vehiculos/{objetivo['id']}",
        json={"activo": False, "precio": objetivo["precio"]},
        headers=h,
    )
    assert r.status_code == 200
    actual = cliente.get(f"/vehiculos/{objetivo['id']}", headers=h).json()
    assert actual["activo"] is True


def test_perfil_password_larga_rechazada():
    h = _headers()
    r = cliente.put("/perfil", json={"password_nueva": "a" * 73}, headers=h)
    assert r.status_code == 422


def test_perfil_cambia_usuario_y_token_sigue_valido():
    """Cambiar el nombre de usuario no invalida la sesion (token por id)."""

    reg = cliente.post(
        "/auth/registro",
        json={"nombre": "Pa", "apellido": "Pe", "correo": "pa@mail.com",
              "usuario": "paco", "password": "Clave123"},
    )
    assert reg.status_code == 200
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assert cliente.put("/perfil", json={"usuario": "paco2"}, headers=h).status_code == 200
    assert cliente.get("/auth/me", headers=h).json()["usuario"] == "paco2"
    assert cliente.post(
        "/auth/login-json", json={"usuario": "paco2", "password": "Clave123"}
    ).status_code == 200
    assert cliente.put("/perfil", json={"usuario": "asesor"}, headers=h).status_code == 409


def test_recalcular_reproduce_resultado():
    """Recalcular una simulacion guardada reproduce los mismos indicadores."""

    h, cli, veh = _ids()
    sim = _crear_sim(h, cli, veh).json()
    re = cliente.post(f"/simulaciones/{sim['id']}/recalcular", headers=h).json()
    assert abs(re["cuota_mensual"] - sim["cuota_mensual"]) < 0.01
    assert abs(re["monto_prestamo"] - sim["monto_prestamo"]) < 0.01
    if sim["tcea"] is not None and re["tcea"] is not None:
        assert abs(re["tcea"] - sim["tcea"]) < 1e-6


def test_editar_simulacion_archivada_no_cambia_estado():
    """Se puede editar una simulacion archivada y su estado no cambia al editar."""

    h, cli, veh = _ids()
    sim = _crear_sim(h, cli, veh).json()
    # Se archiva (baja logica) y luego se edita: el estado debe seguir ARCHIVADA.
    cliente.delete(f"/simulaciones/{sim['id']}", headers=h)
    activo = next(c for c in cli if c["activo"])
    editada = cliente.put(
        f"/simulaciones/{sim['id']}",
        json={**_solicitud_base(activo["id"], _veh_pen(veh)["id"], plan="PLAN_24"), "estado": "CALCULADA"},
        headers=h,
    ).json()
    assert editada["estado"] == "ARCHIVADA"
    assert editada["numero_cuotas"] == 24


def test_editar_cambiando_moneda_convierte_precio_conservado():
    """Al editar cambiando la moneda (sin actualizar precio) el precio se convierte."""

    h, cli, veh = _ids()
    sim = _crear_sim(h, cli, veh).json()  # creada en Soles
    precio_pen = sim["precio_vehiculo"]
    activo = next(c for c in cli if c["activo"])
    editada = cliente.put(
        f"/simulaciones/{sim['id']}",
        json=_solicitud_base(
            activo["id"], _veh_pen(veh)["id"], moneda="USD", tipo_cambio_referencial=4.0
        ),
        headers=h,
    ).json()
    assert editada["moneda"] == "USD"
    # El precio conservado se convirtio de Soles a Dolares (precio_pen / 4.0),
    # no se reutilizo el numero original como si ya estuviera en Dolares.
    assert abs(editada["precio_vehiculo"] - precio_pen / 4.0) < 0.01


def test_cuota_final_mayor_que_saldo_rechazada():
    """Si la cuota inicial es tan alta que el cuoton supera al prestamo, se rechaza."""

    h, cli, veh = _ids()
    activo = next(c for c in cli if c["activo"])
    # Cuota inicial 99%: el prestamo queda en 1% del precio, menor que el cuoton
    # (40% del precio en Plan 36): no queda saldo para las cuotas mensuales.
    r = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(activo["id"], _veh_pen(veh)["id"], porcentaje_cuota_inicial=0.99),
        headers=h,
    )
    assert r.status_code == 400
