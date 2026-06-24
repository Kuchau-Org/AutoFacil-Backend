# AutoFacil - Backend (FastAPI)

## Correr código

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
`AUTOFACIL_CLAVE_SECRETA` (firma de los JWT); cambiar fuera de desarrollo.

## Cuenta de prueba

| Usuario | Contrasena |
|---------|------------|
| demo    | Demo1234   |

## Pruebas

```cmd
venv\Scripts\activate
pytest
```
