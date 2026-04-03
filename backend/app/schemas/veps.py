"""
Schemas de VEPs
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class VEPBase(BaseModel):
    """Schema base para VEP"""
    tipo_vep: str
    periodo: str  # YYYY-MM
    categoria: Optional[str] = None


class VEPCreate(VEPBase):
    """Schema para crear VEP"""
    cliente_id: int
    fecha_vencimiento: Optional[date] = None
    intereses: Optional[Decimal] = None


class VEPUpdate(BaseModel):
    """Schema para actualizar VEP"""
    fecha_pago: Optional[date] = None
    comprobante_pago: Optional[str] = None
    observaciones: Optional[str] = None


class VEPResponse(VEPBase):
    """Schema para respuesta de VEP"""
    id: int
    tenant_id: int
    cliente_id: Optional[int]
    importe_original: Decimal
    intereses: Decimal
    importe_total: Decimal
    estado: str
    numero_vep: Optional[str]
    fecha_vencimiento: Optional[date]
    aprobado_por: Optional[int]
    aprobado_en: Optional[datetime]
    fecha_pago: Optional[date]
    comprobante_pago: Optional[str]
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
