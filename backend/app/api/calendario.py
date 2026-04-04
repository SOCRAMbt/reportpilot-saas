"""
API de Calendario Fiscal — Vencimientos por mes
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import CalendarioVencimiento
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendario", tags=["Calendario Fiscal"])


@router.get("/vencimientos")
async def listar_vencimientos(
    mes: Optional[str] = Query(None, description="Filtrar por mes (YYYY-MM)"),
    organismo: Optional[str] = Query(None, description="Filtrar por organismo (ARCA, ARBA, etc.)"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Listar vencimientos fiscales.

    - **mes**: YYYY-MM (ej: 2026-04)
    - **organismo**: ARCA, ARBA, AGIP, etc.

    Retorna lista ordenada por fecha_efectiva.
    """
    query = select(CalendarioVencimiento)

    if mes:
        try:
            anio, month = map(int, mes.split("-"))
            primer_dia = date(anio, month, 1)
            if month == 12:
                ultimo_dia = date(anio + 1, 1, 1)
            else:
                ultimo_dia = date(anio, month + 1, 1)

            query = query.where(
                CalendarioVencimiento.fecha_efectiva >= primer_dia,
                CalendarioVencimiento.fecha_efectiva < ultimo_dia,
            )
        except (ValueError, TypeError):
            pass

    if organismo:
        query = query.where(CalendarioVencimiento.organismo == organismo.upper())

    # Solo vigentes
    hoy = date.today()
    query = query.where(
        CalendarioVencimiento.vigencia_desde <= hoy,
        (CalendarioVencimiento.vigencia_hasta.is_(None) |
         (CalendarioVencimiento.vigencia_hasta >= hoy)),
    )

    query = query.order_by(CalendarioVencimiento.fecha_efectiva)

    resultado = await db.execute(query)
    vencimientos = resultado.scalars().all()

    return [
        {
            "id": v.id,
            "organismo": v.organismo,
            "tipo_obligacion": v.tipo_obligacion,
            "terminacion_cuit": v.terminacion_cuit,
            "categoria_monotributo": v.categoria_monotributo,
            "fecha_base": v.fecha_base.isoformat() if v.fecha_base else None,
            "fecha_efectiva": v.fecha_efectiva.isoformat() if v.fecha_efectiva else None,
            "es_prorroga": v.es_prorroga,
            "fuente": v.fuente,
        }
        for v in vencimientos
    ]
