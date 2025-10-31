from .soap_client_v2 import SIFENClient
from .parsers import xml_parser, XMLParser
from .redis_cache import redis_cache, RedisCache

# Crear instancia del cliente
sifen_client = SIFENClient()

__all__ = [
    "sifen_client",
    "SIFENClient",
    "xml_parser",
    "XMLParser",
    "redis_cache",
    "RedisCache"
]
