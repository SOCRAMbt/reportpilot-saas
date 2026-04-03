"""
Endpoints de VEPs - Obligaciones Fiscales
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime
from decimal import Decimal

from app.db import get_db
from app.models import VEP, Cliente, ParametroFiscal
from app.api.auth import get_current_user_id, get_current_tenant_id
from app.schemas.veps import VEPResponse, VEPCreate, VEPUpdate

router = APIRouter(prefix="/veps", tags=["VEPs"])


@router.get("", response_model=list[VEPResponse])
async def listar_veps(
    tenant_id: int = Depends(get_current_tenant_id),
    cliente_id: int | None = None,
    periodo: str | None = None,
    estado: str | None = None,
    session: AsyncSession = Depends(get_db)
):
    """Listar VEPs con filtros"""
    query = select(VEP).where(VEP.tenant_id == tenant_id)

    if cliente_id:
        query = query.where(VEP.cliente_id == cliente_id)
    if periodo:
        query = query.where(VEP.periodo == periodo)
    if estado:
        query = query.where(VEP.estado == estado)

    query = query.order_by(VEP.periodo.desc())
    resultado = await session.execute(query)
    return [VEPResponse.model_validate(v) for v in resultado.scalars().all()]


@router.post("/pre-liquidar", response_model=VEPResponse)
async def pre_liquidar_vep(
    data: VEPCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Pre-liquidar VEP para aprobación del cliente
    """
    # Obtener parámetros vigentes
    resultado = await session.execute(
        select(ParametroFiscal).where(
            ParametroFiscal.nombre == "monotributo_cuotas_2026",
            ParametroFiscal.fecha_vigencia_desde <= date.today()
        )
    )
    params = resultado.scalar_one_or_none()

    if not params:
        raise HTTPException(500, "Parámetros fiscales no encontrados")

    # Calcular importe según categoría
    categoria = data.categoria or "A"
    cuotas = params.valor
    importe_base = Decimal(str(cuotas.get(categoria, 0)))

    # Calcular intereses si corresponde
    intereses = data.intereses or Decimal(0)
    importe_total = importe_base + intereses

    vep = VEP(
        tenant_id=tenant_id,
        cliente_id=data.cliente_id,
        tipo_vep=data.tipo_vep,
        periodo=data.periodo,
        categoria=categoria,
        importe_original=importe_base,
        intereses=intereses,
        importe_total=importe_total,
        estado="PRE_LIQUIDADO",
        fecha_vencimiento=data.fecha_vencimiento,
    )

    session.add(vep)
    await session.commit()
    await session.refresh(vep)

    return VEPResponse.model_validate(vep)


@router.post("/{vep_id}/aprobar")
async def aprobar_vep(
    vep_id: int,
    request: Request,
    tenant_id: int = Depends(get_current_tenant_id),
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Aprobar VEP (requiere friction cognitiva para montos altos)
    Captura IP y User-Agent para log de auditoría.
    """
    resultado = await session.execute(
        select(VEP).where(VEP.id == vep_id, VEP.tenant_id == tenant_id)
    )
    vep = resultado.scalar_one_or_none()

    if not vep:
        raise HTTPException(404, "VEP no encontrado")

    # Capturar datos de auditoría
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Actualizar estado
    vep.estado = "APROBADO"
    vep.aprobado_por = user_id
    vep.aprobado_en = datetime.now()
    vep.aprobacion_ip = client_host
    vep.aprobacion_user_agent = user_agent

    await session.commit()
    await session.refresh(vep)

    return {"mensaje": "VEP aprobado", "numero_vep": vep.numero_vep}


@router.put("/{vep_id}/registrar-pago")
async def registrar_pago(
    vep_id: int,
    data: VEPUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """Registrar pago de VEP"""
    resultado = await session.execute(
        select(VEP).where(VEP.id == vep_id, VEP.tenant_id == tenant_id)
    )
    vep = resultado.scalar_one_or_none()

    if not vep:
        raise HTTPException(404, "VEP no encontrado")

    vep.estado = "PAGADO"
    vep.fecha_pago = data.fecha_pago or date.today()
    vep.comprobante_pago = data.comprobante_pago

    await session.commit()
    await session.refresh(vep)

    return VEPResponse.model_validate(vep)
