"""
Módulo ARCO — Solicitudes de Acceso, Rectificación, Cancelación, Oposición
Ley 25.326 de Protección de Datos Personales (Argentina)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import SolicitudARCO
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arco", tags=["ARCO"])

TIPOS_VALIDOS = {"ACCESO", "RECTIFICACION", "CANCELACION", "OPOSICION"}


@router.post("/solicitud", response_model=dict)
async def crear_solicitud_arco(
    body: dict,
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Crear una solicitud ARCO.

    - **tipo**: ACCESO | RECTIFICACION | CANCELACION | OPOSICION
    - **cuit_solicitante**: CUIT de quien solicita
    - **nombre_solicitante**: Nombre completo
    - **email_contacto**: Email para responder
    - **descripcion**: Detalle de la solicitud
    """
    tipo = body.get("tipo", "").upper()
    cuit_solicitante = body.get("cuit_solicitante", "").strip()
    nombre_solicitante = body.get("nombre_solicitante", "").strip()
    email_contacto = body.get("email_contacto", "").strip()
    descripcion = body.get("descripcion", "").strip()

    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Debe ser uno de: {', '.join(sorted(TIPOS_VALIDOS))}"
        )

    if not cuit_solicitante or not cuit_solicitante.replace("-", "").isdigit():
        raise HTTPException(status_code=400, detail="CUIT solicitante inválido")

    if not nombre_solicitante:
        raise HTTPException(status_code=400, detail="Nombre solicitante requerido")

    if not email_contacto or "@" not in email_contacto:
        raise HTTPException(status_code=400, detail="Email contacto inválido")

    # SLA: 5 días hábiles (Ley 25.326)
    # Simplificado: 7 días calendario para cubrir fines de semana
    fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=7)

    solicitud = SolicitudARCO(
        tenant_id=tenant_id,
        tipo=tipo,
        cuit_solicitante=cuit_solicitante,
        nombre_solicitante=nombre_solicitante,
        email_contacto=email_contacto,
        descripcion=descripcion,
        estado="PENDIENTE",
        fecha_vencimiento_sla=fecha_vencimiento,
    )

    session.add(solicitud)
    await session.commit()
    await session.refresh(solicitud)

    return {
        "mensaje": f"Solicitud ARCO ({tipo}) registrada. SLA: 5 días hábiles.",
        "id": solicitud.id,
        "tipo": solicitud.tipo,
        "estado": solicitud.estado,
        "fecha_vencimiento_sla": solicitud.fecha_vencimiento_sla.isoformat() if solicitud.fecha_vencimiento_sla else None,
    }


@router.get("/solicitudes", response_model=list[dict])
async def listar_solicitudes_arco(
    estado: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Listar solicitudes ARCO del tenant con filtros.
    """
    query = select(SolicitudARCO).where(SolicitudARCO.tenant_id == tenant_id)

    if estado:
        query = query.where(SolicitudARCO.estado == estado.upper())
    if tipo:
        query = query.where(SolicitudARCO.tipo == tipo.upper())

    query = query.order_by(SolicitudARCO.creado_en.desc())

    resultado = await session.execute(query)
    solicitudes = resultado.scalars().all()

    return [
        {
            "id": s.id,
            "tipo": s.tipo,
            "cuit_solicitante": s.cuit_solicitante,
            "nombre_solicitante": s.nombre_solicitante,
            "email_contacto": s.email_contacto,
            "estado": s.estado,
            "creado_en": s.creado_en.isoformat() if s.creado_en else None,
            "fecha_vencimiento_sla": s.fecha_vencimiento_sla.isoformat() if s.fecha_vencimiento_sla else None,
        }
        for s in solicitudes
    ]


@router.put("/solicitud/{solicitud_id}/responder", response_model=dict)
async def responder_solicitud_arco(
    solicitud_id: int,
    body: dict,
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Responder una solicitud ARCO.

    - **estado**: COMPLETADA | DENEGADA_LEGAL
    - **motivo_denegacion**: Requerido si estado = DENEGADA_LEGAL
    """
    resultado = await session.execute(
        select(SolicitudARCO).where(
            SolicitudARCO.id == solicitud_id,
            SolicitudARCO.tenant_id == tenant_id
        )
    )
    solicitud = resultado.scalar_one_or_none()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    nuevo_estado = body.get("estado", "").upper()
    if nuevo_estado not in ("COMPLETADA", "DENEGADA_LEGAL"):
        raise HTTPException(status_code=400, detail="Estado debe ser COMPLETADA o DENEGADA_LEGAL")

    if nuevo_estado == "DENEGADA_LEGAL" and not body.get("motivo_denegacion"):
        raise HTTPException(status_code=400, detail="Motivo de denegación requerido")

    solicitud.estado = nuevo_estado
    solicitud.fecha_respuesta = datetime.now(timezone.utc)
    if nuevo_estado == "DENEGADA_LEGAL":
        solicitud.motivo_denegacion = body.get("motivo_denegacion", "")

    await session.commit()

    return {
        "mensaje": f"Solicitud ARCO marcada como {nuevo_estado}",
        "id": solicitud.id,
        "estado": solicitud.estado,
    }
