from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Configuración de la aplicación usando variables de entorno"""
    
    # Ambiente SIFEN
    sifen_environment: Literal["test", "production"] = "test"
    
    # Certificado digital
    cert_pfx_path: str
    cert_password: str
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""  # Vacío por defecto (sin password)
    redis_enabled: bool = True
    redis_ttl_ruc: int = 3600  # 1 hora en segundos
    redis_ttl_dte: int = 7200  # 2 horas en segundos
    
    # URLs de SIFEN
    @property
    def sifen_base_url(self) -> str:
        if self.sifen_environment == "production":
            return "https://sifen.set.gov.py"
        return "https://sifen-test.set.gov.py"
    
    @property
    def sifen_consulta_ruc_url(self) -> str:
        return f"{self.sifen_base_url}/de/ws/consultas/consulta-ruc.wsdl"
    
    @property
    def sifen_consulta_dte_url(self) -> str:
        return f"{self.sifen_base_url}/de/ws/consultas/consulta.wsdl"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()
