import json
import logging
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Servicio de cache Redis para consultas SIFEN"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.enabled = settings.redis_enabled
        
    async def connect(self):
        """Conectar a Redis"""
        if not self.enabled:
            logger.info("Redis cache deshabilitado")
            return
            
        try:
            # Construir URL de conexión Redis
            if settings.redis_password:
                redis_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            else:
                redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            
            self.redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis.ping()
            logger.info(f"Conectado a Redis: {settings.redis_host}:{settings.redis_port}")
            
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.enabled = False
            self.redis = None
    
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Desconectado de Redis")
    
    async def get(self, key: str) -> Optional[dict]:
        """Obtener valor del cache"""
        if not self.enabled or not self.redis:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                logger.info(f"Cache HIT para key: {key}")
                return json.loads(value)
            else:
                logger.info(f"Cache MISS para key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error obteniendo del cache {key}: {e}")
            return None
    
    def _serialize_value(self, value: Any) -> str:
        """Serializa valores para Redis, manejando modelos Pydantic"""
        try:
            # Si es un diccionario, intentar serializar directamente
            if isinstance(value, dict):
                # Convertir cualquier modelo Pydantic en el diccionario
                serializable_dict = {}
                for k, v in value.items():
                    if hasattr(v, 'model_dump'):  # Es un modelo Pydantic
                        serializable_dict[k] = v.model_dump()
                    elif isinstance(v, (list, tuple)):
                        # Manejar listas que pueden contener modelos Pydantic
                        serializable_dict[k] = [
                            item.model_dump() if hasattr(item, 'model_dump') else item
                            for item in v
                        ]
                    else:
                        serializable_dict[k] = v
                return json.dumps(serializable_dict, ensure_ascii=False, default=str)
            
            # Si tiene model_dump (es un modelo Pydantic)
            elif hasattr(value, 'model_dump'):
                return json.dumps(value.model_dump(), ensure_ascii=False, default=str)
            
            # Para otros tipos, usar json.dumps con default=str para manejar tipos no serializables
            else:
                return json.dumps(value, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Error serializando valor: {e}")
            # Fallback: convertir a string
            return json.dumps(str(value), ensure_ascii=False)

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Guardar valor en el cache"""
        if not self.enabled or not self.redis:
            return False
            
        try:
            serialized_value = self._serialize_value(value)
            await self.redis.setex(key, ttl, serialized_value)
            logger.info(f"Cache SET para key: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error guardando en cache {key}: {e}")
            return False
    
    async def delete(self, key: str):
        """Eliminar valor del cache"""
        if not self.enabled or not self.redis:
            return False
            
        try:
            result = await self.redis.delete(key)
            logger.info(f"Cache DELETE para key: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Error eliminando del cache {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """Limpiar claves que coincidan con un patrón"""
        if not self.enabled or not self.redis:
            return 0
            
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                logger.info(f"Cache CLEAR para patrón: {pattern} ({len(keys)} claves)")
                return result
            return 0
        except Exception as e:
            logger.error(f"Error limpiando cache con patrón {pattern}: {e}")
            return 0
    
    def get_ruc_key(self, ruc: str) -> str:
        """Generar clave de cache para RUC"""
        return f"sifen:ruc:{ruc}"
    
    def get_dte_key(self, cdc: str) -> str:
        """Generar clave de cache para DTE"""
        return f"sifen:dte:{cdc}"
    
    async def get_ruc_cache(self, ruc: str) -> Optional[dict]:
        """Obtener RUC del cache"""
        key = self.get_ruc_key(ruc)
        return await self.get(key)
    
    async def set_ruc_cache(self, ruc: str, data: Any) -> bool:
        """Guardar RUC en cache"""
        key = self.get_ruc_key(ruc)
        return await self.set(key, data, settings.redis_ttl_ruc)
    
    async def get_dte_cache(self, cdc: str) -> Optional[dict]:
        """Obtener DTE del cache"""
        key = self.get_dte_key(cdc)
        return await self.get(key)
    
    async def set_dte_cache(self, cdc: str, data: Any) -> bool:
        """Guardar DTE en cache"""
        key = self.get_dte_key(cdc)
        return await self.set(key, data, settings.redis_ttl_dte)
    
    async def health_check(self) -> dict:
        """Verificar estado de Redis"""
        if not self.enabled:
            return {
                "redis_enabled": False,
                "status": "disabled"
            }
        
        if not self.redis:
            return {
                "redis_enabled": True,
                "status": "disconnected",
                "error": "No hay conexión a Redis"
            }
        
        try:
            await self.redis.ping()
            info = await self.redis.info()
            return {
                "redis_enabled": True,
                "status": "connected",
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db
            }
        except Exception as e:
            return {
                "redis_enabled": True,
                "status": "error",
                "error": str(e)
            }


# Instancia global del cache
redis_cache = RedisCache()