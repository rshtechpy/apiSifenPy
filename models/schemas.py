from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class RUCData(BaseModel):
    """Datos del RUC consultado"""
    ruc: str
    razon_social: str
    estado: str
    estado_descripcion: str
    es_facturador_electronico: bool


class RUCResponse(BaseModel):
    """Respuesta de consulta de RUC"""
    success: bool
    codigo: str
    mensaje: str
    data: Optional[RUCData] = None


class EmisorData(BaseModel):
    """Datos del emisor del DTE"""
    ruc: str
    dv: Optional[str] = None  # Dígito verificador del emisor
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


class ReceptorData(BaseModel):
    """Datos del receptor del DTE"""
    nombre: str
    tipo_id: Optional[str] = None
    numero_id: Optional[str] = None
    ruc: Optional[str] = None
    dv: Optional[str] = None  # Dígito verificador del receptor
    direccion: Optional[str] = None
    pais: Optional[str] = None


class ItemData(BaseModel):
    """Item de la factura"""
    codigo: str
    descripcion: str
    cantidad: float
    precio_unitario: float
    total: int
    iva_tipo: Optional[str] = None
    iva_monto: Optional[int] = None


class TotalesData(BaseModel):
    """Totales del documento"""
    total_operacion: int
    total_iva: int
    total_iva_5: Optional[int] = 0
    total_iva_10: Optional[int] = 0
    total_exento: Optional[int] = 0
    total_exonerado: Optional[int] = 0
    moneda: str = "PYG"


class DTEData(BaseModel):
    """Datos del DTE consultado"""
    cdc: str
    numero_autorizacion: str
    codigo_seguridad: Optional[str] = None
    fecha_emision: str
    tipo_documento: str
    numero_documento: str
    establecimiento: Optional[str] = None
    punto_expedicion: Optional[str] = None
    tipo_emision: Optional[str] = None
    condicion_operacion: Optional[str] = None
    emisor: EmisorData
    receptor: ReceptorData
    totales: TotalesData
    items: List[ItemData] = []
    qr_url: Optional[str] = None


class DTEResponse(BaseModel):
    """Respuesta de consulta de DTE"""
    success: bool
    codigo: str
    mensaje: str
    data: Optional[DTEData] = None


class ErrorResponse(BaseModel):
    """Respuesta de error"""
    success: bool = False
    codigo: str
    mensaje: str
    detalle: Optional[str] = None
