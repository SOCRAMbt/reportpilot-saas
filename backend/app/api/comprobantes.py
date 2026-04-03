"""
Endpoints de gestión de comprobantes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import date

from app.db import get_db
from app.models import Comprobante, Cliente, Tenant
from app.api.auth import get_current_user_id, get_current_tenant_id
from app.services.delta_processing import procesar_delta_comprobante, EstadosComprobante
from app.services.ocr import procesar_comprobante_ocr
from app.schemas.comprobantes import (
    ComprobanteCreate,
    ComprobanteResponse,
    ComprobanteListResponse,
    ComprobanteUpdate,
)

router = APIRouter(prefix="/comprobantes", tags=["Comprobantes"])


@router.get("", response_model=ComprobanteListResponse)
async def listar_comprobantes(
    tenant_id: int = Depends(get_current_tenant_id),
    cliente_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    """
    Listar comprobantes con filtros y paginación
    """
    # Construir query base
    query = select(Comprobante).where(Comprobante.tenant_id == tenant_id)

    # Aplicar filtros
    if cliente_id:
        query = query.where(Comprobante.cliente_id == cliente_id)

    if estado:
        query = query.where(Comprobante.estado_interno == estado)

    if fecha_desde:
        query = query.where(Comprobante.fecha_emision >= fecha_desde)

    if fecha_hasta:
        query = query.where(Comprobante.fecha_emision <= fecha_hasta)

    # Ordenar por fecha (más reciente primero)
    query = query.order_by(Comprobante.fecha_emision.desc())

    # Paginación
    offset = (pagina - 1) * limite
    query = query.offset(offset).limit(limite)

    resultado = await session.execute(query)
    comprobantes = resultado.scalars().all()

    # Contar total
    count_query = select(func.count()).select_from(Comprobante).where(
        Comprobante.tenant_id == tenant_id
    )
    if cliente_id:
        count_query = count_query.where(Comprobante.cliente_id == cliente_id)
    if estado:
        count_query = count_query.where(Comprobante.estado_interno == estado)

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return ComprobanteListResponse(
        comprobantes=[ComprobanteResponse.model_validate(c) for c in comprobantes],
        total=total,
        pagina=pagina,
        limite=limite,
        total_paginas=(total + limite - 1) // limite
    )


@router.get("/{comprobante_id}", response_model=ComprobanteResponse)
async def obtener_comprobante(
    comprobante_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Obtener detalle de un comprobante
    """
    resultado = await session.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.tenant_id == tenant_id
        )
    )
    comprobante = resultado.scalar_one_or_none()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado"
        )

    return ComprobanteResponse.model_validate(comprobante)


@router.post("", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED)
async def crear_comprobante(
    data: ComprobanteCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Crear nuevo comprobante (manual o importado)
    """
    # Verificar cliente si se proporciona
    cliente = None
    if data.cliente_id:
        resultado = await session.execute(
            select(Cliente).where(
                Cliente.id == data.cliente_id,
                Cliente.tenant_id == tenant_id
            )
        )
        cliente = resultado.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado"
            )

    # Obtener CUIT del tenant para cuit_receptor
    resultado_tenant = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = resultado_tenant.scalar_one_or_none()
    cuit_receptor_defecto = tenant.cuit if tenant else None

    # Procesar delta para verificar duplicados
    comprobante_datos = data.model_dump()
    estado_interno, observaciones = await procesar_delta_comprobante(
        session, tenant_id, comprobante_datos, EstadosComprobante.PRESENTE_VALIDO
    )

    # Si es duplicado exacto, rechazar
    if estado_interno == EstadosComprobante.ANULADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comprobante duplicado ya existe en el sistema"
        )

    # Crear comprobante
    comprobante = Comprobante(
        tenant_id=tenant_id,
        cliente_id=data.cliente_id,
        tipo_comprobante=data.tipo_comprobante,
        punto_venta=data.punto_venta,
        numero=data.numero,
        cuit_emisor=data.cuit_emisor or (cliente.cuit if cliente else None),
        cuit_receptor=data.cuit_receptor or cuit_receptor_defecto,
        fecha_emision=data.fecha_emision,
        total=data.total,
        neto_gravado=data.neto_gravado or 0,
        neto_exento=data.neto_exento or 0,
        neto_no_gravado=data.neto_no_gravado or 0,
        iva=data.iva or 0,
        estado_interno=estado_interno,
        estado_arca=EstadosComprobante.PRESENTE_VALIDO,
        origen="manual",
        observaciones=observaciones,
    )

    session.add(comprobante)
    await session.commit()
    await session.refresh(comprobante)

    return ComprobanteResponse.model_validate(comprobante)


@router.post("/ocr", response_model=ComprobanteResponse)
async def procesar_ocr(
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Procesar comprobante con OCR (IA)

    Sube imagen/PDF de factura y extrae datos automáticamente.
    """
    # Verificar tipo de archivo
    if not file.content_type or not file.content_type.startswith("image/"):
        if not file.filename.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo debe ser imagen (JPG, PNG) o PDF"
            )

    # Leer archivo
    contenido = await file.read()

    # Procesar con OCR
    try:
        ocr_result = await procesar_comprobante_ocr(tenant_id, contenido)
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando OCR: {str(e)}"
        )

    # Validar resultado
    valido, errores = ocr_result.validar()

    if not valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OCR no pudo extraer datos válidos: {errores}"
        )

    # Verificar texto sospechoso (prompt injection)
    if ocr_result.texto_sospechoso_detectado:
        # Crear comprobante pero marcar para revisión
        observaciones = f"Texto sospechoso detectado: {ocr_result.texto_sospechoso_detectado}"
    else:
        observaciones = None

    # Crear comprobante con datos del OCR
    comprobante = Comprobante(
        tenant_id=tenant_id,
        tipo_comprobante=ocr_result.tipo_comprobante,
        punto_venta=ocr_result.punto_venta,
        numero=ocr_result.numero,
        cuit_emisor=ocr_result.cuit_emisor,  # Ya viene tokenizado
        fecha_emision=ocr_result.fecha_emision,
        total=ocr_result.total,
        neto_gravado=ocr_result.neto_gravado,
        iva=ocr_result.iva,
        estado_interno=EstadosComprobante.PENDIENTE_VERIFICACION,
        estado_arca=EstadosComprobante.AUSENTE,  # Pendiente de consultar ARCA
        origen="ocr",
        observaciones=observaciones,
        metadata={
            "confidence": ocr_result.confidence,
            "archivo_original": file.filename,
        }
    )

    session.add(comprobante)
    await session.commit()
    await session.refresh(comprobante)

    return ComprobanteResponse.model_validate(comprobante)


@router.put("/{comprobante_id}", response_model=ComprobanteResponse)
async def actualizar_comprobante(
    comprobante_id: int,
    data: ComprobanteUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Actualizar comprobante existente
    """
    resultado = await session.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.tenant_id == tenant_id
        )
    )
    comprobante = resultado.scalar_one_or_none()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado"
        )

    # Actualizar campos permitidos
    update_data = data.model_dump(exclude_unset=True)

    for campo, valor in update_data.items():
        if valor is not None:
            setattr(comprobante, campo, valor)

    await session.commit()
    await session.refresh(comprobante)

    return ComprobanteResponse.model_validate(comprobante)


@router.delete("/{comprobante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_comprobante(
    comprobante_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Eliminar/Anular comprobante
    """
    resultado = await session.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.tenant_id == tenant_id
        )
    )
    comprobante = resultado.scalar_one_or_none()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado"
        )

    # Marcar como anulado (soft delete)
    comprobante.estado_interno = EstadosComprobante.ANULADO

    await session.commit()

    return None
