from .soap_client_v2 import SIFENClient
from .parsers import xml_parser, XMLParser

# Crear instancia del cliente
sifen_client = SIFENClient()

__all__ = [
    "sifen_client",
    "SIFENClient",
    "xml_parser",
    "XMLParser"
]
