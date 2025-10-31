# SIFEN API Wrapper

API REST en FastAPI para consultar servicios de facturación electrónica de Paraguay (SIFEN).

## Características

- ✅ Consulta de RUC (datos del contribuyente)
- ✅ Consulta de DTE por CDC (documento tributario electrónico)
- ✅ Respuestas en JSON
- ✅ Autenticación con certificado digital
- ✅ Soporte para ambientes TEST y PRODUCCIÓN

## Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Ambiente: test o production
SIFEN_ENVIRONMENT=test

# Certificado digital (ruta relativa o absoluta)
CERT_PFX_PATH=./certificados/certificado.pfx
CERT_PASSWORD=tu_password_aqui
```

## Uso

```bash
# Iniciar servidor
uvicorn main:app --reload

# La API estará disponible en: http://localhost:8000
# Documentación interactiva: http://localhost:8000/docs
```

## Endpoints

### 1. Consultar RUC

```bash
GET /api/ruc/{ruc}
```

**Ejemplo:**
```bash
curl http://localhost:8000/api/ruc/1011758
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "ruc": "1011758",
    "razon_social": "ARMIN CLAR BENKENSTEIN",
    "estado": "ACT",
    "estado_descripcion": "ACTIVO",
    "es_facturador_electronico": false
  }
}
```

### 2. Consultar DTE por CDC

```bash
GET /api/dte/{cdc}
```

**Ejemplo:**
```bash
curl http://localhost:8000/api/dte/01010117580003004013660612025102615903
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "cdc": "01010117580003004013660612025102615903",
    "numero_autorizacion": "2702547197",
    "fecha_emision": "2025-10-26T05:21:53",
    "tipo_documento": "Factura electrónica",
    "emisor": {
      "ruc": "1011758-0",
      "nombre": "ARMIN CLAR BENKENSTEIN",
      "direccion": "RUTA PROYECTO 1418, KM 18,5"
    },
    "receptor": {
      "nombre": "OLIVIA KLEIM",
      "tipo_id": "Cédula extranjera",
      "numero_id": "12429411"
    },
    "totales": {
      "total_operacion": 6600,
      "total_iva": 314,
      "moneda": "PYG"
    },
    "items": [
      {
        "codigo": "226220",
        "descripcion": "LECHE SEM.DESCR. LA FORTUNA UAT DE 1LTS",
        "cantidad": 1.0,
        "precio_unitario": 6600.0,
        "total": 6600
      }
    ]
  }
}
```

## Estructura del Proyecto

```
sifen-api/
├── main.py              # Aplicación principal FastAPI
├── config.py            # Configuración y variables de entorno
├── services/
│   ├── __init__.py
│   ├── soap_client.py   # Cliente SOAP para SIFEN
│   └── parsers.py       # Parsers XML a JSON
├── models/
│   ├── __init__.py
│   └── schemas.py       # Modelos Pydantic
├── certificados/        # Directorio para certificados (no commitear)
│   └── .gitkeep
├── .env                 # Variables de entorno (no commitear)
├── .env.example         # Ejemplo de configuración
├── .gitignore
├── requirements.txt
└── README.md
```

## Seguridad

⚠️ **IMPORTANTE:**
- Nunca commitear archivos `.pfx` o `.p12` al repositorio
- Nunca commitear el archivo `.env` con contraseñas
- Usar variables de entorno para datos sensibles
- El certificado debe tener permisos de lectura restringidos

## Licencia

MIT
