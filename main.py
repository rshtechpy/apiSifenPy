from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Union
from contextlib import asynccontextmanager

from config import settings
from models import RUCResponse, DTEResponse, ErrorResponse
from services import sifen_client, xml_parser, redis_cache

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("Iniciando aplicación...")
    await redis_cache.connect()
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")
    await redis_cache.disconnect()


# Crear aplicación FastAPI
app = FastAPI(
    title="SIFEN API Wrapper",
    description="API REST para consultar servicios de facturación electrónica de Paraguay (SIFEN)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
    redis_status = await redis_cache.health_check()
    
    return {
        "status": "ok",
        "ambiente": settings.sifen_environment,
        "redis": redis_status
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
        
        # Intentar obtener del cache primero
        cached_data = await redis_cache.get_ruc_cache(ruc)
        if cached_data:
            logger.info(f"RUC {ruc} obtenido del cache")
            parsed = cached_data
        else:
            logger.info(f"RUC {ruc} no encontrado en cache, consultando SIFEN")
            # Llamar al servicio SOAP
            xml_response = sifen_client.consultar_ruc(ruc)
            
            # Parsear respuesta
            parsed = xml_parser.parse_ruc_response(xml_response)
            
            # Guardar en cache solo si la consulta fue exitosa
            if parsed['codigo'] == '0502':
                await redis_cache.set_ruc_cache(ruc, parsed)
        
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
        
        # Intentar obtener del cache primero
        cached_data = await redis_cache.get_dte_cache(cdc)
        if cached_data:
            logger.info(f"DTE {cdc} obtenido del cache")
            parsed = cached_data
        else:
            logger.info(f"DTE {cdc} no encontrado en cache, consultando SIFEN")
            # Llamar al servicio SOAP
            xml_response = sifen_client.consultar_dte(cdc)
            
            # Parsear respuesta
            parsed = xml_parser.parse_dte_response(xml_response)
            
            # Guardar en cache solo si la consulta fue exitosa
            if parsed['codigo'] == '0422':
                await redis_cache.set_dte_cache(cdc, parsed)
        
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


@app.delete(
    "/api/cache/ruc/{ruc}",
    summary="Limpiar cache RUC",
    description="Elimina la información de un RUC específico del cache"
)
async def clear_ruc_cache(
    ruc: str = Path(
        ...,
        description="RUC del contribuyente",
        min_length=5,
        max_length=8,
        regex="^[0-9]+$"
    )
):
    """Elimina un RUC específico del cache"""
    try:
        key = redis_cache.get_ruc_key(ruc)
        deleted = await redis_cache.delete(key)
        
        return {
            "success": True,
            "message": f"Cache del RUC {ruc} {'eliminado' if deleted else 'no encontrado'}",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"Error limpiando cache RUC {ruc}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando cache: {str(e)}"
        )


@app.delete(
    "/api/cache/dte/{cdc}",
    summary="Limpiar cache DTE",
    description="Elimina la información de un DTE específico del cache"
)
async def clear_dte_cache(
    cdc: str = Path(
        ...,
        description="Código de Control del documento",
        min_length=44,
        max_length=44,
        regex="^[0-9]+$"
    )
):
    """Elimina un DTE específico del cache"""
    try:
        key = redis_cache.get_dte_key(cdc)
        deleted = await redis_cache.delete(key)
        
        return {
            "success": True,
            "message": f"Cache del DTE {cdc} {'eliminado' if deleted else 'no encontrado'}",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"Error limpiando cache DTE {cdc}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando cache: {str(e)}"
        )


@app.delete(
    "/api/cache/all",
    summary="Limpiar todo el cache",
    description="Elimina toda la información del cache de SIFEN"
)
async def clear_all_cache():
    """Elimina todo el cache relacionado con SIFEN"""
    try:
        deleted_ruc = await redis_cache.clear_pattern("sifen:ruc:*")
        deleted_dte = await redis_cache.clear_pattern("sifen:dte:*")
        
        return {
            "success": True,
            "message": "Cache limpiado completamente",
            "deleted_ruc": deleted_ruc,
            "deleted_dte": deleted_dte,
            "total_deleted": deleted_ruc + deleted_dte
        }
    except Exception as e:
        logger.error(f"Error limpiando todo el cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando cache: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
