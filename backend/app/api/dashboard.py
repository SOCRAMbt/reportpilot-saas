"""
API de Dashboard - Estadísticas y métricas del estudio
"""

import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Comprobante, VEP, Alerta, Cliente
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=dict)
async def obtener_estadisticas(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Obtener estadísticas del dashboard

    Retorna:
    - Comprobantes procesados hoy
    - Pendientes de revisión
    - VEPs a vencer esta semana
    - Clientes en riesgo
    - Alertas activas
    - Facturación del mes
    """
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    # 1. Comprobantes procesados hoy
    result_hoy = await db.execute(
        select(func.count(Comprobante.id)).where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha_emision == hoy,
            Comprobante.estado_interno == "INCORPORADO"
        )
    )
    comprobantes_hoy = result_hoy.scalar() or 0

    # 2. Pendientes de revisión (Delta)
    result_pendientes = await db.execute(
        select(func.count(Comprobante.id)).where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.estado_interno.in_(["REVISION_HUMANA", "PENDIENTE_VERIFICACION"])
        )
    )
    pendientes_revision = result_pendientes.scalar() or 0

    # 3. VEPs a vencer en 7 días
    vencimiento_semana = hoy + timedelta(days=7)
    result_veps = await db.execute(
        select(func.count(VEP.id)).where(
            VEP.tenant_id == tenant_id,
            VEP.estado.in_(["PRE_LIQUIDADO", "APROBADO"]),
            VEP.fecha_vencimiento >= hoy,
            VEP.fecha_vencimiento <= vencimiento_semana
        )
    )
    veps_pendientes = result_veps.scalar() or 0

    # 4. Alertas activas (no leídas)
    result_alertas = await db.execute(
        select(func.count(Alerta.id)).where(
            Alerta.tenant_id == tenant_id,
            Alerta.leida == False,
            Alerta.archivada == False
        )
    )
    alertas_activas = result_alertas.scalar() or 0

    # 5. Clientes en riesgo fiscal
    # (simplificado: clientes con alertas de riesgo)
    result_riesgo = await db.execute(
        select(func.count(func.distinct(Alerta.cliente_id))).where(
            Alerta.tenant_id == tenant_id,
            Alerta.tipo.like("%riesgo%"),
            Alerta.leida == False
        )
    )
    clientes_en_riesgo = result_riesgo.scalar() or 0

    # 6. Facturación del mes actual
    result_facturacion = await db.execute(
        select(func.sum(Comprobante.total)).where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha_emision >= inicio_mes,
            Comprobante.estado_interno == "INCORPORADO",
            Comprobante.tipo_comprobante.in_(["1", "2", "3", "A", "B", "C"])  # Facturas
        )
    )
    facturacion_mes = result_facturacion.scalar() or 0

    return {
        "comprobantes_hoy": comprobantes_hoy,
        "pendientes_revision": pendientes_revision,
        "veps_pendientes": veps_pendientes,
        "alertas_activas": alertas_activas,
        "clientes_en_riesgo": clientes_en_riesgo,
        "facturacion_mes_actual": float(facturacion_mes) if facturacion_mes else 0.0
    }


@router.get("/actividad", response_model=dict)
async def obtener_actividad_reciente(
    dias: int = Query(7, ge=1, le=30, description="Días a consultar"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Obtener actividad reciente del estudio
    """
    fecha_desde = date.today() - timedelta(days=dias)

    # Comprobantes por día
    result_comprobantes = await db.execute(
        select(
            Comprobante.fecha_emision,
            func.count(Comprobante.id).label("cantidad")
        ).where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha_emision >= fecha_desde
        ).group_by(Comprobante.fecha_emision).order_by(Comprobante.fecha_emision)
    )
    comprobantes_por_dia = [
        {"fecha": row[0].isoformat(), "cantidad": row[1]}
        for row in result_comprobantes.all()
    ]

    # Alertas por día
    result_alertas = await db.execute(
        select(
            func.date(Alerta.creado_en).label("fecha"),
            func.count(Alerta.id).label("cantidad")
        ).where(
            Alerta.tenant_id == tenant_id,
            Alerta.creado_en >= fecha_desde
        ).group_by(func.date(Alerta.creado_en)).order_by(func.date(Alerta.creado_en))
    )
    alertas_por_dia = [
        {"fecha": row[0].isoformat() if row[0] else None, "cantidad": row[1]}
        for row in result_alertas.all()
    ]

    return {
        "comprobantes_por_dia": comprobantes_por_dia,
        "alertas_por_dia": alertas_por_dia
    }


@router.get("/semaforo-clientes")
async def semaforo_clientes(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Vista semáforo para persona física: qué necesita atención HOY cada cliente.
    """
    import datetime
    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)

    resultado = await db.execute(
        select(Cliente).where(Cliente.tenant_id == tenant_id, Cliente.activo == True)
        .order_by(Cliente.razon_social)
    )
    clientes = resultado.scalars().all()

    semaforo = []
    for c in clientes:
        issues = []
        color = "verde"

        cbtes_mes = await db.execute(
            select(func.count()).select_from(Comprobante).where(
                Comprobante.cliente_id == c.id,
                Comprobante.tenant_id == tenant_id,
                Comprobante.fecha_emision >= primer_dia_mes,
            )
        )
        if cbtes_mes.scalar() == 0:
            issues.append("Sin comprobantes este mes")
            color = "rojo"

        pendientes = await db.execute(
            select(func.count()).select_from(Comprobante).where(
                Comprobante.cliente_id == c.id,
                Comprobante.tenant_id == tenant_id,
                Comprobante.estado_interno == "REVISION_HUMANA",
            )
        )
        if pendientes.scalar() > 0:
            issues.append(f"{pendientes.scalar()} comprobantes sin revisar")
            if color != "rojo":
                color = "amarillo"

        veps_pendientes = await db.execute(
            select(func.count()).select_from(VEP).where(
                VEP.cliente_id == c.id,
                VEP.tenant_id == tenant_id,
                VEP.estado == "PRE_LIQUIDADO",
            )
        )
        if veps_pendientes.scalar() > 0:
            issues.append(f"{veps_pendientes.scalar()} VEP(s) pendientes")
            if color != "rojo":
                color = "amarillo"

        semaforo.append({
            "id": c.id,
            "cuit": c.cuit,
            "razon_social": c.razon_social,
            "categoria_monotributo": c.categoria_monotributo,
            "color": color,
            "issues": issues,
            "acciones": issues if issues else ["Al día"],
        })

    return {
        "semaforo": semaforo,
        "totales": {
            "rojo": sum(1 for x in semaforo if x["color"] == "rojo"),
            "amarillo": sum(1 for x in semaforo if x["color"] == "amarillo"),
            "verde": sum(1 for x in semaforo if x["color"] == "verde"),
        }
    }
