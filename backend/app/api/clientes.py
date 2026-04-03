"""
API de Clientes - Gestión de clientes del estudio
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Cliente, Comprobante, Alerta
from app.services.motor_fiscal import analizar_riesgo_fiscal
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clientes", tags=["clientes"])


# ============================================
# SCHEMAS
# ============================================

class ClienteSchema:
    """Schema básico de cliente"""
    id: int
    tenant_id: int
    cuit: str
    razon_social: str
    nombre_fantasia: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    categoria_monotributo: Optional[str]
    activo: bool


# ============================================
# ENDPOINTS
# ============================================

@router.get("", response_model=List[dict])
async def listar_clientes(
    busqueda: Optional[str] = Query(None, description="Buscar por nombre o CUIT"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría monotributo"),
    activo: bool = Query(True, description="Solo clientes activos"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Listar clientes del estudio con filtros y paginación

    - **busqueda**: Busca por nombre o CUIT
    - **categoria**: Filtra por categoría de Monotributo
    - **activo**: Si es True, solo muestra clientes activos
    """
    # Construir query base
    query = select(Cliente).where(Cliente.tenant_id == tenant_id)

    # Filtros
    if activo:
        query = query.where(Cliente.activo == True)

    if categoria:
        query = query.where(Cliente.categoria_monotributo == categoria)

    if busqueda:
        # Búsqueda por CUIT exacta o parcial
        if busqueda.isdigit():
            query = query.where(
                or_(
                    Cliente.cuit.like(f"%{busqueda}%"),
                    Cliente.razon_social.ilike(f"%{busqueda}%"),
                    Cliente.nombre_fantasia.ilike(f"%{busqueda}%"),
                )
            )
        else:
            # Búsqueda por nombre
            query = query.where(
                or_(
                    Cliente.razon_social.ilike(f"%{busqueda}%"),
                    Cliente.nombre_fantasia.ilike(f"%{busqueda}%"),
                )
            )

    # Paginación
    query = query.order_by(Cliente.razon_social).offset((pagina - 1) * limite).limit(limite)

    # Ejecutar
    resultado = await db.execute(query)
    clientes = resultado.scalars().all()

    # Contar total
    count_query = select(func.count()).select_from(Cliente).where(Cliente.tenant_id == tenant_id)
    if activo:
        count_query = count_query.where(Cliente.activo == True)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "clientes": [cliente_to_dict(c) for c in clientes],
        "total": total,
        "pagina": pagina,
        "total_paginas": (total + limite - 1) // limite
    }


@router.get("/{cliente_id}", response_model=dict)
async def obtener_cliente(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Obtener detalle de un cliente con análisis de riesgo fiscal
    """
    # Obtener cliente
    resultado = await db.execute(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        )
    )
    cliente = resultado.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Obtener análisis de riesgo fiscal
    try:
        analisis = await analizar_riesgo_fiscal(db, cliente_id)
        riesgo_fiscal = {
            "categoria_actual": analisis.categoria_actual,
            "categoria_calculada": analisis.categoria_calculada,
            "ingresos_ultimos_12_meses": float(analisis.ingresos_ultimos_12_meses),
            "riesgo_exclusion": analisis.riesgo_exclusion,
            "urgencia_alerta": analisis.urgencia_alerta,
            "ventana_exclusion": analisis.ventana_exclusion,
            "triggers_activados": analisis.triggers_activados,
            "recomendacion": analisis.recomendacion
        }
    except Exception as e:
        logger.error(f"Error calculando riesgo fiscal: {e}")
        riesgo_fiscal = {"error": str(e)}

    # Obtener comprobantes del mes
    from datetime import date, timedelta
    fecha_desde = date.today() - timedelta(days=30)
    
    comp_result = await db.execute(
        select(func.count(Comprobante.id)).where(
            Comprobante.cliente_id == cliente_id,
            Comprobante.fecha_emision >= fecha_desde
        )
    )
    comprobantes_mes = comp_result.scalar() or 0

    return {
        **cliente_to_dict(cliente),
        "riesgo_fiscal": riesgo_fiscal,
        "comprobantes_mes": comprobantes_mes
    }


@router.post("", response_model=dict)
async def crear_cliente(
    cliente_data: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Crear nuevo cliente
    """
    # Validar CUIT único para el tenant
    existe = await db.execute(
        select(Cliente).where(
            Cliente.tenant_id == tenant_id,
            Cliente.cuit == cliente_data.get("cuit")
        )
    )
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El CUIT ya existe para este estudio")

    # Crear cliente
    cliente = Cliente(
        tenant_id=tenant_id,
        cuit=cliente_data.get("cuit"),
        razon_social=cliente_data.get("razon_social"),
        nombre_fantasia=cliente_data.get("nombre_fantasia"),
        tipo_persona=cliente_data.get("tipo_persona", "fisica"),
        tipo_responsable=cliente_data.get("tipo_responsable"),
        email=cliente_data.get("email"),
        telefono=cliente_data.get("telefono"),
        domicilio=cliente_data.get("domicilio"),
        localidad=cliente_data.get("localidad"),
        provincia=cliente_data.get("provincia"),
        codigo_postal=cliente_data.get("codigo_postal"),
        fecha_inicio_actividades=cliente_data.get("fecha_inicio_actividades"),
        categoria_monotributo=cliente_data.get("categoria_monotributo"),
        activo=True
    )

    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)

    return cliente_to_dict(cliente)


@router.put("/{cliente_id}", response_model=dict)
async def actualizar_cliente(
    cliente_id: int,
    cliente_data: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Actualizar datos de un cliente
    """
    # Obtener cliente
    resultado = await db.execute(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        )
    )
    cliente = resultado.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Actualizar campos
    campos_permitidos = [
        "razon_social", "nombre_fantasia", "tipo_persona", "tipo_responsable",
        "email", "telefono", "domicilio", "localidad", "provincia",
        "codigo_postal", "fecha_inicio_actividades", "categoria_monotributo",
        "activo", "configuracion"
    ]

    for campo in campos_permitidos:
        if campo in cliente_data:
            setattr(cliente, campo, cliente_data[campo])

    await db.commit()
    await db.refresh(cliente)

    return cliente_to_dict(cliente)


@router.get("/{cliente_id}/comprobantes", response_model=dict)
async def obtener_comprobantes_cliente(
    cliente_id: int,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Obtener comprobantes de un cliente
    """
    # Verificar cliente
    resultado = await db.execute(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        )
    )
    cliente = resultado.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Obtener comprobantes
    from sqlalchemy import select
    query = select(Comprobante).where(
        Comprobante.cliente_id == cliente_id
    ).order_by(Comprobante.fecha_emision.desc()).offset((pagina - 1) * limite).limit(limite)

    comp_result = await db.execute(query)
    comprobantes = comp_result.scalars().all()

    # Contar total
    count_result = await db.execute(
        select(func.count()).where(Comprobante.cliente_id == cliente_id)
    )
    total = count_result.scalar()

    return {
        "comprobantes": [
            {
                "id": c.id,
                "tipo_comprobante": c.tipo_comprobante,
                "punto_venta": c.punto_venta,
                "numero": c.numero,
                "fecha_emision": c.fecha_emision.isoformat() if c.fecha_emision else None,
                "total": float(c.total) if c.total else 0,
                "estado_interno": c.estado_interno,
                "estado_arca": c.estado_arca,
            }
            for c in comprobantes
        ],
        "total": total,
        "pagina": pagina,
        "total_paginas": (total + limite - 1) // limite
    }


@router.post("/{cliente_id}/relacion-arca", response_model=dict)
async def registrar_relacion_arca(
    cliente_id: int,
    servicios: list[str],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Registrar que un cliente otorgó Relación Delegada en ARCA.
    El cliente ya lo hizo desde su cuenta ARCA — esto solo lo registra en el sistema.
    """
    from app.models import RelacionARCA
    from app.services.arca import arca_service

    # Verificar que el cliente existe y pertenece al tenant
    resultado = await db.execute(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        )
    )
    cliente = resultado.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Verificar relación en ARCA (padrón)
    verificada = False
    try:
        padron = await arca_service.padron_a4_consultar(db, tenant_id, cliente.cuit)
        verificada = bool(padron.get("cuit"))
    except Exception as e:
        logger.warning(f"No se pudo verificar relación ARCA: {e}")

    # Buscar o crear RelacionARCA
    resultado_rel = await db.execute(
        select(RelacionARCA).where(
            RelacionARCA.tenant_id == tenant_id,
            RelacionARCA.cliente_id == cliente_id
        )
    )
    relacion = resultado_rel.scalar_one_or_none()

    from datetime import date, datetime, timezone
    from sqlalchemy import select as sa_select

    if relacion:
        relacion.servicios_delegados = servicios
        relacion.activa = True
        relacion.verificada_ok = verificada
        relacion.fecha_ultima_verificacion = datetime.now(timezone.utc)
    else:
        relacion = RelacionARCA(
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            cuit_cliente=cliente.cuit,
            servicios_delegados=servicios,
            activa=True,
            verificada_ok=verificada,
            fecha_alta=date.today(),
            fecha_ultima_verificacion=datetime.now(timezone.utc)
        )
        db.add(relacion)

    await db.commit()

    mensaje = "Relación registrada"
    if verificada:
        mensaje += " y verificada en ARCA"
    else:
        mensaje += " (verificación pendiente — ARCA puede estar caído)"

    return {"mensaje": mensaje, "verificada_ok": verificada}


@router.get("/{cliente_id}/relacion-arca", response_model=dict)
async def obtener_relacion_arca(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Obtener estado de la Relación Delegada ARCA de un cliente.
    """
    from app.models import RelacionARCA

    resultado = await db.execute(
        select(RelacionARCA).where(
            RelacionARCA.tenant_id == tenant_id,
            RelacionARCA.cliente_id == cliente_id
        )
    )
    relacion = resultado.scalar_one_or_none()

    if not relacion:
        return {"activa": False, "mensaje": "No hay relación delegada registrada"}

    return {
        "activa": relacion.activa,
        "verificada_ok": relacion.verificada_ok,
        "servicios_delegados": relacion.servicios_delegados,
        "fecha_alta": relacion.fecha_alta.isoformat() if relacion.fecha_alta else None,
        "fecha_ultima_verificacion": relacion.fecha_ultima_verificacion.isoformat() if relacion.fecha_ultima_verificacion else None,
        "error_ultimo": relacion.error_ultimo,
    }


# ============================================
# UTILIDADES
# ============================================

def cliente_to_dict(cliente: Cliente) -> dict:
    """Convertir Cliente a diccionario"""
    return {
        "id": cliente.id,
        "tenant_id": cliente.tenant_id,
        "cuit": cliente.cuit,
        "razon_social": cliente.razon_social,
        "nombre_fantasia": cliente.nombre_fantasia,
        "tipo_persona": cliente.tipo_persona,
        "tipo_responsable": cliente.tipo_responsable,
        "email": cliente.email,
        "telefono": cliente.telefono,
        "domicilio": cliente.domicilio,
        "localidad": cliente.localidad,
        "provincia": cliente.provincia,
        "codigo_postal": cliente.codigo_postal,
        "fecha_inicio_actividades": cliente.fecha_inicio_actividades.isoformat() if cliente.fecha_inicio_actividades else None,
        "categoria_monotributo": cliente.categoria_monotributo,
        "activo": cliente.activo,
    }
