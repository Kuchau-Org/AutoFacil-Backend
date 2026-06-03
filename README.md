# AutoFacil - Backend (FastAPI)

API de simulacion de credito vehicular (metodo frances vencido ordinario).

## Puesta en marcha

```cmd
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- API: http://localhost:8000 - Docs: http://localhost:8000/docs
- La base SQLite (`autofacil.db`) y los datos de ejemplo se crean al iniciar.

## Variables de entorno

Prefijo `AUTOFACIL_` (ver `.env.example`). La clave importante es
`AUTOFACIL_CLAVE_SECRETA` (firma de los JWT); cambiela fuera de desarrollo.

## Cuentas de prueba

| Usuario | Contrasena |
|---------|------------|
| demo    | Demo1234   |
| maria   | Maria1234  |

## Aislamiento de datos

Cada asesor gestiona su propia cartera: sus clientes, su catalogo de vehiculos
y sus simulaciones. Un asesor no ve ni puede operar los datos de otro.

## Pruebas

```cmd
venv\Scripts\activate
pytest
```

## Notas

- Producto Compra Inteligente: credito frances vencido ordinario con cuota balon
  opcional (un porcentaje del precio del vehiculo se difiere al pago final).
  Meses comerciales de 30 dias. La tasa de interes es FIJA (efectiva o nominal;
  si es nominal, la capitalizacion es obligatoria).
- Moneda del credito independiente de la del vehiculo: el mismo auto puede
  simularse en Soles o Dolares; el precio se convierte con el tipo de cambio,
  que queda guardado en la simulacion.
- Cargos configurables (todos opcionales, inician en 0): gastos de terceros
  (notariales, registrales, tasacion) que se financian; GPS con instalacion
  (cargo unico al desembolso), mantenimiento (mensual, en la cuota) y reposicion
  (tarifario referencial que NO se cobra); seguro vehicular mensual; y seguro de
  desgravamen (solo con consentimiento, Res. SBS 890-2025). Todos los cargos
  configurados forman parte de la TCEA (salvo la reposicion del GPS y la tasa
  moratoria, que son informativas).
- Estados de simulacion: CALCULADA (vigente) y ARCHIVADA (baja logica que
  conserva el historial). No hay borrado definitivo: DELETE archiva. AutoFacil es
  un simulador de propuestas, no un sistema de aprobacion ni de inventario.
- El vehiculo no maneja estado comercial: solo `activo` (baja logica). Se puede
  editar y recalcular propuestas historicas aunque el vehiculo se haya dado de
  baja; se conserva el precio original salvo que se pida actualizarlo.
- Token JWT con `tipo="acceso"`; el enlace publico usa `tipo="compartir"` y solo
  muestra propuestas calculadas (las archivadas devuelven 410).
- VAN y TCEA segun transparencia SBS (del deudor). La hoja resumen del cliente
  detalla los cargos, la tasa moratoria (nominal anual no capitalizable) y los
  datos de la poliza (art. 25 del Reglamento de Transparencia).
- Migracion ligera para SQLite: al iniciar se agregan columnas faltantes y se
  normalizan estados antiguos (`app/migraciones.py`), sin perder datos previos.
- Tipo de cambio en linea: solo USD/PEN (API publica con respaldo local).