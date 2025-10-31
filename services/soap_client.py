import requests
from typing import Dict, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class SIFENClient:
    """Cliente SOAP para interactuar con los servicios de SIFEN"""
    
    def __init__(self):
        self.cert_path = settings.cert_pfx_path
        self.cert_password = settings.cert_password
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Crear sesión con certificado configurado"""
        session = requests.Session()
        
        # Si el certificado es PFX, requests no lo soporta directamente
        # Necesitamos convertirlo o usar una librería que lo soporte
        # Por ahora usamos cert como tupla (cert_file, key_file) si están separados
        # O configuramos según el formato del certificado
        
        session.headers.update({
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        })
        
        return session
    
    def _build_soap_envelope(self, body: str) -> str:
        """Construir envelope SOAP"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:xsd="http://ekuatia.set.gov.py/sifen/xsd">
    <soap:Header/>
    <soap:Body>
        {body}
    </soap:Body>
</soap:Envelope>"""
    
    def consultar_ruc(self, ruc: str) -> str:
        """
        Consultar datos de un RUC en SIFEN
        
        Args:
            ruc: RUC sin dígito verificador (solo números)
        
        Returns:
            XML response como string
        """
        body = f"""<xsd:rEnviConsRUC>
            <xsd:dId>1</xsd:dId>
            <xsd:dRUCCons>{ruc}</xsd:dRUCCons>
        </xsd:rEnviConsRUC>"""
        
        soap_request = self._build_soap_envelope(body)
        
        logger.info(f"Consultando RUC: {ruc}")
        
        try:
            # Para usar certificado PFX con requests, necesitamos extraer cert y key
            # O usar una librería como pyOpenSSL
            response = self.session.post(
                settings.sifen_consulta_ruc_url,
                data=soap_request.encode('utf-8'),
                cert=self._get_cert_tuple(),  # Implementar según formato del cert
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando RUC {ruc}: {e}")
            raise
    
    def consultar_dte(self, cdc: str) -> str:
        """
        Consultar DTE por CDC en SIFEN
        
        Args:
            cdc: Código de Control del documento (44 caracteres)
        
        Returns:
            XML response como string
        """
        body = f"""<xsd:rEnviConsDeRequest>
            <xsd:dId>1</xsd:dId>
            <xsd:dCDC>{cdc}</xsd:dCDC>
        </xsd:rEnviConsDeRequest>"""
        
        # Usar namespace diferente para este endpoint
        soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">
    <env:Header/>
    <env:Body>
        <ns:rEnviConsDeRequest xmlns:ns="http://ekuatia.set.gov.py/sifen/xsd">
            <ns:dId>1</ns:dId>
            <ns:dCDC>{cdc}</ns:dCDC>
        </ns:rEnviConsDeRequest>
    </env:Body>
</env:Envelope>"""
        
        logger.info(f"Consultando DTE: {cdc}")
        
        try:
            response = self.session.post(
                settings.sifen_consulta_dte_url,
                data=soap_request.encode('utf-8'),
                cert=self._get_cert_tuple(),
                verify=True,
                timeout=30
            )
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando DTE {cdc}: {e}")
            raise
    
    def _get_cert_tuple(self) -> Optional[tuple]:
        """
        Obtener tupla de certificado para requests
        
        Si el certificado es PFX, necesitamos extraer el cert y key
        Por ahora retornamos None y manejamos según el formato
        """
        # TODO: Implementar extracción de cert/key desde PFX si es necesario
        # O usar cryptography para manejar el PFX
        return None  # Por ahora, configurar manualmente


# Instancia global del cliente
sifen_client = SIFENClient()
