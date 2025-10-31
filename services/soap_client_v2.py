import requests
from typing import Optional, Tuple
from pathlib import Path
from config import settings
import logging
import tempfile
import os
import time
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption

logger = logging.getLogger(__name__)


class SIFENClient:
    """Cliente SOAP para interactuar con los servicios de SIFEN"""
    
    def __init__(self):
        self.cert_path = settings.cert_pfx_path
        self.cert_password = settings.cert_password
        self.cert_pem_path = None
        self.key_pem_path = None
        self._request_counter = int(time.time())  # Inicializar contador con timestamp
        self._extract_pfx_to_pem()
        self.session = self._create_session()
    
    def _get_next_id(self) -> int:
        """Generar siguiente ID autoincremental"""
        self._request_counter += 1
        return self._request_counter
    
    def _extract_pfx_to_pem(self):
        """
        Extraer certificado y clave privada del archivo PFX a archivos PEM temporales
        Esto es necesario porque requests no soporta PFX directamente
        """
        try:
            pfx_path = Path(self.cert_path)
            
            if not pfx_path.exists():
                raise FileNotFoundError(f"Certificado no encontrado: {self.cert_path}")
            
            # Leer el archivo PFX
            with open(pfx_path, 'rb') as f:
                pfx_data = f.read()
            
            # Extraer certificado y clave privada
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                pfx_data,
                self.cert_password.encode() if self.cert_password else None
            )
            
            # Crear archivos temporales para cert y key
            # Usar directorio temporal del sistema
            temp_dir = tempfile.gettempdir()
            
            # Guardar certificado
            self.cert_pem_path = os.path.join(temp_dir, 'sifen_cert.pem')
            with open(self.cert_pem_path, 'wb') as f:
                f.write(certificate.public_bytes(Encoding.PEM))
            
            # Guardar clave privada
            self.key_pem_path = os.path.join(temp_dir, 'sifen_key.pem')
            with open(self.key_pem_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=NoEncryption()
                ))
            
            logger.info("Certificado PFX extraído exitosamente a archivos PEM temporales")
            
        except Exception as e:
            logger.error(f"Error extrayendo certificado PFX: {e}")
            raise
    
    def _create_session(self) -> requests.Session:
        """Crear sesión con certificado configurado"""
        session = requests.Session()
        
        session.headers.update({
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        })
        
        return session
    
    def _get_cert_tuple(self) -> Tuple[str, str]:
        """
        Obtener tupla de certificado para requests
        Returns: (cert_path, key_path)
        """
        if not self.cert_pem_path or not self.key_pem_path:
            raise ValueError("Certificado no extraído correctamente")
        
        return (self.cert_pem_path, self.key_pem_path)
    
    def consultar_ruc(self, ruc: str) -> str:
        """
        Consultar datos de un RUC en SIFEN
        
        Args:
            ruc: RUC sin dígito verificador (solo números)
        
        Returns:
            XML response como string
        """
        request_id = self._get_next_id()
        soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsd="http://ekuatia.set.gov.py/sifen/xsd">
    <soap:Header/>
    <soap:Body>
        <xsd:rEnviConsRUC>
            <xsd:dId>{request_id}</xsd:dId>
            <xsd:dRUCCons>{ruc}</xsd:dRUCCons>
        </xsd:rEnviConsRUC>
    </soap:Body>
</soap:Envelope>"""
        
        logger.info(f"Consultando RUC: {ruc} con dId: {request_id}")
        logger.debug(f"URL: {settings.sifen_consulta_ruc_url}")
        logger.debug(f"SOAP Request: {soap_request}")
        
        try:
            response = self.session.post(
                settings.sifen_consulta_ruc_url,
                data=soap_request.encode('utf-8'),
                cert=self._get_cert_tuple(),
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            logger.info(f"Respuesta recibida para RUC {ruc}: {response.status_code}")
            logger.debug(f"XML Response: {response.text}")
            return response.text
            
        except requests.exceptions.SSLError as e:
            logger.error(f"Error SSL consultando RUC {ruc}: {e}")
            raise Exception(f"Error de certificado SSL: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando RUC {ruc}: {e}")
            raise Exception(f"Error en la petición: {str(e)}")
    
    def consultar_dte(self, cdc: str) -> str:
        """
        Consultar DTE por CDC en SIFEN
        
        Args:
            cdc: Código de Control del documento (44 caracteres)
        
        Returns:
            XML response como string
        """
        request_id = self._get_next_id()
        soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">
    <env:Header/>
    <env:Body>
        <ns:rEnviConsDeRequest xmlns:ns="http://ekuatia.set.gov.py/sifen/xsd">
            <ns:dId>{request_id}</ns:dId>
            <ns:dCDC>{cdc}</ns:dCDC>
        </ns:rEnviConsDeRequest>
    </env:Body>
</env:Envelope>"""
        
        logger.info(f"Consultando DTE: {cdc} con dId: {request_id}")
        logger.debug(f"URL: {settings.sifen_consulta_dte_url}")
        logger.debug(f"SOAP Request: {soap_request}")
        
        try:
            response = self.session.post(
                settings.sifen_consulta_dte_url,
                data=soap_request.encode('utf-8'),
                cert=self._get_cert_tuple(),
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            logger.info(f"Respuesta recibida para DTE {cdc}: {response.status_code}")
            logger.debug(f"XML Response: {response.text}")
            return response.text
            
        except requests.exceptions.SSLError as e:
            logger.error(f"Error SSL consultando DTE {cdc}: {e}")
            raise Exception(f"Error de certificado SSL: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando DTE {cdc}: {e}")
            raise Exception(f"Error en la petición: {str(e)}")
    
    def __del__(self):
        """Limpiar archivos temporales al destruir el objeto"""
        try:
            if self.cert_pem_path and os.path.exists(self.cert_pem_path):
                os.remove(self.cert_pem_path)
            if self.key_pem_path and os.path.exists(self.key_pem_path):
                os.remove(self.key_pem_path)
        except Exception as e:
            logger.warning(f"Error limpiando archivos temporales: {e}")


# Instancia global del cliente
sifen_client = SIFENClient()
