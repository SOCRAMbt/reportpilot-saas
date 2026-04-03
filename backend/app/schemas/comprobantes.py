"""
Schemas de comprobantes
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import date, datetime
from decimal import Decimal


class ComprobanteBase(BaseModel):
    """Schema base para comprobante"""
    tipo_comprobante: str
    punto_venta: int
    numero: int
    fecha_emision: date
    total: Decimal
    neto_gravado: Optional[Decimal] = None
    neto_exento: Optional[Decimal] = None
    neto_no_gravado: Optional[Decimal] = None
    iva: Optional[Decimal] = None
    cuit_emisor: Optional[str] = None
    cuit_receptor: Optional[str] = None


class ComprobanteCreate(ComprobanteBase):
    """Schema para crear comprobante"""
    cliente_id: Optional[int] = None


class ComprobanteUpdate(BaseModel):
    """Schema para actualizar comprobante"""
    tipo_comprobante: Optional[str] = None
    punto_venta: Optional[int] = None
    numero: Optional[int] = None
    fecha_emision: Optional[date] = None
    total: Optional[Decimal] = None
    neto_gravado: Optional[Decimal] = None
    iva: Optional[Decimal] = None
    observaciones: Optional[str] = None
    estado_interno: Optional[str] = None


class ComprobanteResponse(ComprobanteBase):
    """Schema para respuesta de comprobante"""
    id: int
    tenant_id: int
    cliente_id: Optional[int]
    estado_arca: str
    estado_interno: str
    cae: Optional[str]
    cae_vencimiento: Optional[date]
    origen: str
    observaciones: Optional[str]
    metadata: dict[str, Any] = {}
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True


class ComprobanteListResponse(BaseModel):
    """Schema para listado de comprobantes"""
    comprobantes: list[ComprobanteResponse]
    total: int
    pagina: int
    limite: int
    total_paginas: int
