from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Union

from config import settings
from models import RUCResponse, DTEResponse, ErrorResponse
from services import sifen_client, xml_parser

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="SIFEN API Wrapper",
    description="API REST para consultar servicios de facturación electrónica de Paraguay (SIFEN)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "nombre": "SIFEN API Wrapper",
        "version": "1.0.0",
        "ambiente": settings.sifen_environment,
        "endpoints": {
            "consultar_ruc": "/api/ruc/{ruc}",
            "consultar_dte": "/api/dte/{cdc}",
            "documentacion": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "ambiente": settings.sifen_environment
    }


@app.get(
    "/api/ruc/{ruc}",
    response_model=RUCResponse,
    responses={
        200: {"description": "RUC encontrado exitosamente"},
        400: {"description": "RUC inválido"},
        404: {"description": "RUC no encontrado"},
        500: {"description": "Error interno del servidor"}
    },
    summary="Consultar RUC",
    description="Consulta los datos de un RUC en el sistema SIFEN"
)
async def consultar_ruc(
    ruc: str = Path(
        ...,
        description="RUC del contribuyente (sin dígito verificador, 5-8 dígitos)",
        min_length=5,
        max_length=8,
        regex="^[0-9]+$"
    )
):
    """
    Consulta los datos de un RUC en SIFEN.
    
    - **ruc**: Número de RUC sin dígito verificador (solo números, 5-8 dígitos)
    
    Retorna:
    - Código de respuesta (0502 = éxito, 0500 = no existe, 0501 = sin permiso)
    - Mensaje descriptivo
    - Datos del RUC si existe (razón social, estado, si es facturador electrónico)
    """
    try:
        logger.info(f"Consultando RUC: {ruc}")
        
        # Llamar al servicio SOAP
        xml_response = sifen_client.consultar_ruc(ruc)
        
        # Parsear respuesta
        parsed = xml_parser.parse_ruc_response(xml_response)
        
        # Construir respuesta
        response = RUCResponse(
            success=parsed['codigo'] == '0502',
            codigo=parsed['codigo'],
            mensaje=parsed['mensaje'],
            data=parsed['data']
        )
        
        # Si el RUC no existe, retornar 404
        if parsed['codigo'] == '0500':
            return JSONResponse(
                status_code=404,
                content=response.model_dump()
            )
        
        # Si no tiene permiso, retornar 403
        if parsed['codigo'] == '0501':
            return JSONResponse(
                status_code=403,
                content=response.model_dump()
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error consultando RUC {ruc}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando RUC: {str(e)}"
        )


@app.get(
    "/api/dte/{cdc}",
    response_model=DTEResponse,
    responses={
        200: {"description": "DTE encontrado exitosamente"},
        400: {"description": "CDC inválido"},
        404: {"description": "DTE no encontrado o rechazado"},
        500: {"description": "Error interno del servidor"}
    },
    summary="Consultar DTE por CDC",
    description="Consulta un Documento Tributario Electrónico por su Código de Control (CDC)"
)
async def consultar_dte(
    cdc: str = Path(
        ...,
        description="Código de Control del documento (44 caracteres)",
        min_length=44,
        max_length=44,
        regex="^[0-9]+$"
    )
):
    """
    Consulta un DTE (Documento Tributario Electrónico) por su CDC.
    
    - **cdc**: Código de Control del documento (44 dígitos)
    
    Retorna:
    - Código de respuesta (0422 = encontrado, 0420 = no existe/rechazado)
    - Mensaje descriptivo
    - Datos completos del DTE si existe (emisor, receptor, items, totales, etc.)
    """
    try:
        logger.info(f"Consultando DTE: {cdc}")
        
        # Llamar al servicio SOAP
        xml_response = sifen_client.consultar_dte(cdc)
        
        # Parsear respuesta
        parsed = xml_parser.parse_dte_response(xml_response)
        
        # Construir respuesta
        response = DTEResponse(
            success=parsed['codigo'] == '0422',
            codigo=parsed['codigo'],
            mensaje=parsed['mensaje'],
            data=parsed['data']
        )
        
        # Si el DTE no existe o fue rechazado, retornar 404
        if parsed['codigo'] == '0420':
            return JSONResponse(
                status_code=404,
                content=response.model_dump()
            )
        
        # Si no tiene permiso para consultar, retornar 403
        if parsed['codigo'] == '0421':
            return JSONResponse(
                status_code=403,
                content=response.model_dump()
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error consultando DTE {cdc}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando DTE: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
