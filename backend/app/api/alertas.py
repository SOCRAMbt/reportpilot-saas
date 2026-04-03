"""
Endpoints de gestión de alertas
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import Alerta
from app.api.auth import get_current_tenant_id

router = APIRouter(prefix="/alertas", tags=["Alertas"])

logger = logging.getLogger(__name__)


@router.get("")
async def list_alertas(
    leida: bool | None = Query(None),
    severidad: str | None = Query(None),
    limite: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Listar alertas del tenant con filtros opcionales.

    - **leida**: filtrar por estado de lectura (None = todas)
    - **severidad**: filtrar por severidad (alta, media, baja)
    - **limite**: maximo de resultados (1-100)
    """
    query = (
        select(Alerta)
        .where(Alerta.tenant_id == tenant_id, Alerta.archivada == False)
        .order_by(Alerta.creado_en.desc())
        .limit(limite)
    )

    if leida is not None:
        query = query.where(Alerta.leida == leida)

    if severidad is not None:
        query = query.where(Alerta.severidad == severidad)

    result = await session.execute(query)
    alertas = result.scalars().all()

    return [
        {
            "id": a.id,
            "tipo": a.tipo,
            "severidad": a.severidad,
            "titulo": a.titulo,
            "mensaje": a.mensaje,
            "leida": a.leida,
            "creado_en": a.creado_en,
        }
        for a in alertas
    ]


@router.post("/{alerta_id}/leida")
async def mark_leida(
    alerta_id: int,
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Marcar una alerta como leida.
    """
    result = await session.execute(
        select(Alerta).where(Alerta.id == alerta_id, Alerta.tenant_id == tenant_id)
    )
    alerta = result.scalar_one_or_none()

    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta no encontrada",
        )

    from datetime import datetime, timezone

    alerta.leida = True
    alerta.leida_en = datetime.now(timezone.utc)
    await session.commit()

    logger.info("alerta marcada como leida", alerta_id=alerta_id, tenant_id=tenant_id)

    return {"mensaje": "Alerta marcada como leída"}


@router.post("/{alerta_id}/archivar")
async def archivar_alerta(
    alerta_id: int,
    session: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Archivar una alerta.
    """
    result = await session.execute(
        select(Alerta).where(Alerta.id == alerta_id, Alerta.tenant_id == tenant_id)
    )
    alerta = result.scalar_one_or_none()

    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta no encontrada",
        )

    alerta.archivada = True
    await session.commit()

    logger.info("alerta archivada", alerta_id=alerta_id, tenant_id=tenant_id)

    return {"mensaje": "Alerta archivada"}
