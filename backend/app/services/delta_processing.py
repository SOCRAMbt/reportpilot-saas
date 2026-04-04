"""
Delta-Processing v9.7 - Sistema de validación de comprobantes

Implementa:
- 7 estados de comprobante según ARCA
- Comparación de 6 campos críticos (no binaria)
- Lock distribuido en Redis para prevenir race conditions
- Re-verificación automática a T+7 y T+30 días
- Prevención de duplicados con tolerancia del 1%
"""

import hashlib
import logging
import redis
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Any, TYPE_CHECKING
from contextlib import contextmanager

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comprobante, Cliente, Alerta
from app.core.config import settings

if TYPE_CHECKING:
    from app.services.arca_service import ARCAService

logger = logging.getLogger(__name__)


# ============================================
# ESTADOS DEL SISTEMA v9.7
# ============================================

class EstadosComprobante:
    """Estados posibles de un comprobante según ARCA"""

    # Estados de ARCA
    PRESENTE_VALIDO = "PRESENTE_VALIDO"
    PRESENTE_ANULADO = "PRESENTE_ANULADO"
    RECHAZADO_ARCA = "RECHAZADO_ARCA"
    AUSENTE = "AUSENTE"
    CONTINGENTE_PENDIENTE = "CONTINGENTE_PENDIENTE"
    DESPACHO_ADUANA = "DESPACHO_ADUANA"
    NC_SIN_CORRELATO = "NC_SIN_CORRELATO"

    # Estados internos
    PENDIENTE_VERIFICACION = "PENDIENTE_VERIFICACION"
    REVISION_HUMANA = "REVISION_HUMANA"
    INCORPORADO = "INCORPORADO"
    ANULADO = "ANULADO"

    # Mapeo de acciones
    ACCIONES = {
        PRESENTE_VALIDO: "DESCARTAR_DUPLICADO",
        PRESENTE_ANULADO: "DESCARTAR_ANULADO",
        RECHAZADO_ARCA: "BLOQUEADO_CAE_INVALIDO",
        AUSENTE: "REVISION_HUMANA_OBLIGATORIA",
        CONTINGENTE_PENDIENTE: "INCORPORAR_CON_ADVERTENCIA",
        DESPACHO_ADUANA: "REVISION_HUMANA_OBLIGATORIA",
        NC_SIN_CORRELATO: "INCORPORAR_CON_ADVERTENCIA",
    }


# ============================================
# CAMPOS CRÍTICOS PARA COMPARACIÓN
# ============================================

CAMPOS_CRITICOS = [
    "cuit_emisor",
    "punto_venta",
    "numero",
    "tipo_comprobante",
    "total",  # Con tolerancia del 1%
    "fecha_emision",
]


def calcular_hash_delta(
    cuit_emisor: str,
    punto_venta: int,
    numero: int
) -> str:
    """
    Calcular hash único para lock distribuido

    Args:
        cuit_emisor: CUIT del emisor
        punto_venta: Punto de venta
        numero: Número de comprobante

    Returns:
        str: Hash SHA-256 (64 caracteres)
    """
    clave = f"{cuit_emisor}:{punto_venta}:{numero}"
    return hashlib.sha256(clave.encode()).hexdigest()


def comparar_comprobantes(
    existente: Comprobante,
    nuevo: dict[str, Any]
) -> tuple[bool, list[str]]:
    """
    Comparar 6 campos críticos entre comprobante existente y nuevo

    La comparación NO es binaria - cualquier discrepancia en campos
    críticos genera REVISION_HUMANA.

    ⚠️ SEGURIDAD: Los logs NUNCA deben incluir CUITs completos.
    Se usan hashes parciales para debugging.

    Args:
        existente: Comprobante en base de datos
        nuevo: Datos del nuevo comprobante

    Returns:
        tuple[bool, list[str]]: (son_iguales, lista_de_discrepancias)
    """
    discrepancias = []
    campos_discrepantes = []

    # 1. CUIT Emisor - ⚠️ NUNCA loguear CUIT completo
    if existente.cuit_emisor != nuevo.get("cuit_emisor"):
        # Usar hash parcial para debugging, nunca el CUIT real
        cuit_hash = existente.cuit_emisor[:4] + "***" if existente.cuit_emisor else "NULL"
        discrepancias.append(f"CUIT emisor: {cuit_hash} != ***")
        campos_discrepantes.append("cuit_emisor")

    # 2. Punto de venta
    if existente.punto_venta != nuevo.get("punto_venta"):
        discrepancias.append(f"PtoVta: {existente.punto_venta} != {nuevo.get('punto_venta')}")
        campos_discrepantes.append("punto_venta")

    # 3. Número
    if existente.numero != nuevo.get("numero"):
        discrepancias.append(f"Nro: {existente.numero} != {nuevo.get('numero')}")
        campos_discrepantes.append("numero")

    # 4. Tipo de comprobante
    if existente.tipo_comprobante != nuevo.get("tipo_comprobante"):
        discrepancias.append(f"Tipo: {existente.tipo_comprobante} != {nuevo.get('tipo_comprobante')}")
        campos_discrepantes.append("tipo_comprobante")

    # 5. Total (con tolerancia del 1%)
    total_existente = float(existente.total) if existente.total else 0
    total_nuevo = float(nuevo.get("total", 0))
    if total_existente > 0:
        diff = abs(total_existente - total_nuevo) / total_existente
        if diff > 0.01:  # 1% de tolerancia
            discrepancias.append(f"Total: ${total_existente:.2f} != ${total_nuevo:.2f} (diff: {diff:.2%})")
            campos_discrepantes.append("total")

    # 6. Fecha de emisión
    if isinstance(existente.fecha_emision, date):
        fecha_existente = existente.fecha_emision
    else:
        fecha_existente = datetime.strptime(existente.fecha_emision, "%Y-%m-%d").date() if existente.fecha_emision else None

    fecha_nueva = nuevo.get("fecha_emision")
    if isinstance(fecha_nueva, str):
        fecha_nueva = datetime.strptime(fecha_nueva, "%Y-%m-%d").date()

    if fecha_existente != fecha_nueva:
        discrepancias.append(f"Fecha: {fecha_existente} != {fecha_nueva}")
        campos_discrepantes.append("fecha_emision")

    son_iguales = len(campos_discrepantes) == 0

    # Log seguro: solo campos discrepantes, sin datos sensibles
    if not son_iguales:
        logger.debug(f"Discrepancias en campos: {', '.join(campos_discrepantes)}")
    else:
        logger.debug("Comparación: IGUALES")

    return son_iguales, discrepancias


# ============================================
# LOCK DISTRIBUIDO (Redis)
# ============================================

@contextmanager
def lock_distribuido(hash_delta: str, timeout: int = 60):
    """
    Context manager para lock distribuido en Redis

    Previene race conditions cuando múltiples workers
    procesan el mismo comprobante simultáneamente.

    Args:
        hash_delta: Hash del comprobante
        timeout: TTL del lock en segundos

    Yields:
        bool: True si obtuvo el lock, False si ya está bloqueado
    """
    redis_client = redis.from_url(settings.redis_url)
    lock_key = f"lock:delta:{hash_delta}"

    # Intentar adquirir lock (SET NX EX)
    adquirido = redis_client.set(lock_key, "1", nx=True, ex=timeout)

    try:
        yield adquirido is not None
    finally:
        if adquirido:
            redis_client.delete(lock_key)


# ============================================
# PROCESAMIENTO DELTA v9.7
# ============================================

async def procesar_delta_comprobante(
    session: AsyncSession,
    tenant_id: int,
    comprobante_datos: dict[str, Any],
    estado_arca: str
) -> tuple[str, Optional[str]]:
    """
    Procesar comprobante según estado en ARCA

    Implementa la lógica de delta-processing v9.7:
    1. Calcular hash delta
    2. Adquirir lock distribuido
    3. Buscar comprobante existente
    4. Comparar 6 campos críticos
    5. Aplicar regla de negocio según estado

    Args:
        session: Sesión de BD
        tenant_id: ID del tenant
        comprobante_datos: Datos del comprobante
        estado_arca: Estado reportado por ARCA

    Returns:
        tuple[str, Optional[str]]: (estado_interno, observaciones)
    """
    # Calcular hash para lock
    hash_delta = calcular_hash_delta(
        comprobante_datos["cuit_emisor"],
        comprobante_datos["punto_venta"],
        comprobante_datos["numero"]
    )

    # Adquirir lock distribuido
    with lock_distribuido(hash_delta) as obtenido:
        if not obtenido:
            logger.warning(f"Lock no obtenido para {hash_delta[:16]} - reintentar")
            return EstadosComprobante.PENDIENTE_VERIFICACION, "Lock distribuido ocupado"

        # Buscar comprobante existente por hash delta
        resultado = await session.execute(
            select(Comprobante).where(
                Comprobante.hash_delta == hash_delta,
                Comprobante.tenant_id == tenant_id,
                Comprobante.estado_interno != EstadosComprobante.ANULADO
            )
        )
        existente = resultado.scalar_one_or_none()

        if existente:
            # Ya existe - comparar campos
            son_iguales, discrepancias = comparar_comprobantes(existente, comprobante_datos)

            if son_iguales:
                # Duplicado exacto - aplicar regla según estado ARCA
                return await _procesar_duplicado(
                    session, tenant_id, existente, estado_arca
                )
            else:
                # Discrepancia - REVISION_HUMANA
                observaciones = f"Discrepancias detectadas: {'; '.join(discrepancias)}"
                await _crear_alerta(
                    session, tenant_id,
                    "discrepancia_campos",
                    "Discrepancia en campos críticos",
                    observaciones,
                    comprobante_id=existente.id
                )
                return EstadosComprobante.REVISION_HUMANA, observaciones

        else:
            # No existe - es nuevo
            return await _procesar_nuevo(
                session, tenant_id, comprobante_datos, estado_arca, hash_delta
            )


async def _procesar_duplicado(
    session: AsyncSession,
    tenant_id: int,
    existente: Comprobante,
    estado_arca: str
) -> tuple[str, Optional[str]]:
    """
    Procesar comprobante duplicado según estado ARCA

    Args:
        session: Sesión de BD
        tenant_id: ID del tenant
        existente: Comprobante existente
        estado_arca: Estado desde ARCA

    Returns:
        tuple[str, Optional[str]]: (nuevo_estado, observaciones)
    """
    accion = EstadosComprobante.ACCIONES.get(estado_arca, "REVISION_HUMANA")

    logger.info(f"Duplicado detectado - Acción: {accion} - Estado ARCA: {estado_arca}")

    # Reglas según estado
    if estado_arca == EstadosComprobante.PRESENTE_VALIDO:
        # Duplicado válido - descartar
        return EstadosComprobante.ANULADO, "Duplicado de comprobante válido existente"

    elif estado_arca == EstadosComprobante.PRESENTE_ANULADO:
        # Ambos anulados
        return EstadosComprobante.ANULADO, "Comprobante anulado en ARCA"

    elif estado_arca == EstadosComprobante.RECHAZADO_ARCA:
        # Distinguir tipo de rechazo
        return EstadosComprobante.REVISION_HUMANA, "CAE inválido según ARCA"

    elif estado_arca == EstadosComprobante.AUSENTE:
        # Ausente - re-verificar a 48hs y 15 días
        return EstadosComprobante.REVISION_HUMANA, "Comprobante ausente en ARCA - re-verificar"

    elif estado_arca == EstadosComprobante.CONTINGENTE_PENDIENTE:
        # Zona de baja conectividad
        return EstadosComprobante.PENDIENTE_VERIFICACION, "Contingente - pendiente de confirmación"

    else:
        # Casos raros - revisión humana
        return EstadosComprobante.REVISION_HUMANA, f"Estado ARCA no estándar: {estado_arca}"


async def _procesar_nuevo(
    session: AsyncSession,
    tenant_id: int,
    comprobante_datos: dict[str, Any],
    estado_arca: str,
    hash_delta: str
) -> tuple[str, Optional[str]]:
    """
    Procesar comprobante nuevo

    Args:
        session: Sesión de BD
        tenant_id: ID del tenant
        comprobante_datos: Datos del comprobante
        estado_arca: Estado desde ARCA
        hash_delta: Hash delta calculado

    Returns:
        tuple[str, Optional[str]]: (estado_interno, observaciones)
    """
    # Todos los nuevos comienzan en PENDIENTE_VERIFICACION
    # Mínimo 7 días antes de incorporarse automáticamente

    observaciones = None

    if estado_arca == EstadosComprobante.CONTINGENTE_PENDIENTE:
        observaciones = "Comprobante contingente - re-verificar a 48hs"

    elif estado_arca == EstadosComprobante.DESPACHO_ADUANA:
        observaciones = "Despacho de aduana - requiere validación manual"

    elif estado_arca == EstadosComprobante.NC_SIN_CORRELATO:
        observaciones = "NC sin correlato físico - validar contablemente"

    return EstadosComprobante.PENDIENTE_VERIFICACION, observaciones


# ============================================
# RE-VERIFICACIÓN AUTOMÁTICA
# ============================================

async def ejecutar_re_verificaciones(session: AsyncSession):
    """
    Ejecutar re-verificaciones automáticas (T+7 y T+30)

    Se ejecuta diariamente vía Celery Beat.
    Consulta estado real en ARCA vía WSCDC.
    """
    from sqlalchemy import select
    from app.services.arca import ARCAService
    from app.services.delta_processing import EstadosComprobante

    arca_service = ARCAService()

    # Re-verificación T+7
    fecha_t7 = (datetime.now() - timedelta(days=7)).date()

    resultado = await session.execute(
        select(Comprobante).where(
            Comprobante.estado_interno == EstadosComprobante.PENDIENTE_VERIFICACION,
            Comprobante.fecha_emision >= fecha_t7,
            Comprobante.fecha_emision <= (datetime.now() - timedelta(days=6)).date()
        )
    )

    pendientes_t7 = resultado.scalars().all()
    logger.info(f"Re-verificación T+7: {len(pendientes_t7)} comprobantes a verificar")

    for comprobante in pendientes_t7:
        try:
            logger.info(f"Re-verificación T+7: {comprobante.hash_delta[:16]}")

            # Consultar estado en ARCA vía WSCDC
            # WSCDC permite consultar por CUIT + tipo + punto_venta + numero
            estado_arca = await _consultar_estado_en_arca(
                arca_service, session, comprobante.tenant_id, comprobante
            )

            if estado_arca:
                # Actualizar estado del comprobante
                comprobante.estado_arca = estado_arca["estado"]
                comprobante.estado_arca_detalle = estado_arca.get("detalle")
                comprobante.fecha_consulta_arca = datetime.now()
                comprobante.cae = estado_arca.get("cae")

                # Si está presente válido, cambiar estado interno
                if estado_arca["estado"] == EstadosComprobante.PRESENTE_VALIDO:
                    comprobante.estado_interno = EstadosComprobante.INCORPORADO
                    logger.info(f"Comprobante {comprobante.id} incorporado automáticamente")
                elif estado_arca["estado"] == EstadosComprobante.RECHAZADO_ARCA:
                    comprobante.estado_interno = EstadosComprobante.REVISION_HUMANA
                    await _crear_alerta(
                        session, comprobante.tenant_id,
                        "rechazo_arca",
                        "Comprobante rechazado en ARCA (T+7)",
                        f"CAE inválido o rechazado: {estado_arca.get('detalle', 'Sin detalle')}",
                        comprobante_id=comprobante.id
                    )

                await session.commit()

        except Exception as e:
            logger.error(f"Error en re-verificación T+7 para comprobante {comprobante.id}: {e}")
            await session.rollback()

    # Re-verificación T+30
    fecha_t30 = (datetime.now() - timedelta(days=30)).date()

    resultado = await session.execute(
        select(Comprobante).where(
            Comprobante.estado_interno == EstadosComprobante.PENDIENTE_VERIFICACION,
            Comprobante.fecha_emision <= fecha_t30
        )
    )

    pendientes_t30 = resultado.scalars().all()
    logger.info(f"Re-verificación T+30: {len(pendientes_t30)} comprobantes a verificar")

    for comprobante in pendientes_t30:
        try:
            logger.info(f"Re-verificación T+30: {comprobante.hash_delta[:16]}")

            # Consultar estado en ARCA vía WSCDC
            estado_arca = await _consultar_estado_en_arca(
                arca_service, session, comprobante.tenant_id, comprobante
            )

            if estado_arca:
                comprobante.estado_arca = estado_arca["estado"]
                comprobante.estado_arca_detalle = estado_arca.get("detalle")
                comprobante.fecha_consulta_arca = datetime.now()
                comprobante.cae = estado_arca.get("cae")

                if estado_arca["estado"] == EstadosComprobante.PRESENTE_VALIDO:
                    comprobante.estado_interno = EstadosComprobante.INCORPORADO
                    logger.info(f"Comprobante {comprobante.id} incorporado automáticamente (T+30)")
                elif estado_arca["estado"] == EstadosComprobante.AUSENTE:
                    # Ausente después de 30 días - alerta crítica
                    comprobante.estado_interno = EstadosComprobante.REVISION_HUMANA
                    await _crear_alerta(
                        session, comprobante.tenant_id,
                        "ausente_arca_t30",
                        "Comprobante AUSENTE en ARCA por 30 días",
                        f"El comprobante no figura en ARCA después de 30 días. Requiere revisión urgente.",
                        comprobante_id=comprobante.id,
                        severidad="critica"
                    )
                elif estado_arca["estado"] == EstadosComprobante.RECHAZADO_ARCA:
                    comprobante.estado_interno = EstadosComprobante.REVISION_HUMANA
                    await _crear_alerta(
                        session, comprobante.tenant_id,
                        "rechazo_arca_t30",
                        "Comprobante RECHAZADO en ARCA (T+30)",
                        f"CAE inválido o rechazado: {estado_arca.get('detalle', 'Sin detalle')}",
                        comprobante_id=comprobante.id,
                        severidad="alta"
                    )

                await session.commit()

        except Exception as e:
            logger.error(f"Error en re-verificación T+30 para comprobante {comprobante.id}: {e}")
            await session.rollback()


async def _consultar_estado_en_arca(
    arca_service: "ARCAService",
    session: AsyncSession,
    tenant_id: int,
    comprobante: Comprobante
) -> Optional[dict[str, Any]]:
    """
    Consultar estado de comprobante en ARCA vía WSCDC

    Args:
        arca_service: Instancia de ARCAService
        session: Sesión de BD
        tenant_id: ID del tenant
        comprobante: Comprobante a verificar

    Returns:
        dict | None: Estado del comprobante o None si no encontrado
    """
    try:
        # WSCDC requiere período como (año, mes), no fechas individuales
        if comprobante.fecha_emision is None:
            logger.warning(f"Comprobante {comprobante.id} sin fecha_emision")
            return None

        anio = comprobante.fecha_emision.year
        mes = comprobante.fecha_emision.month
        periodo = (anio, mes)

        resultado = await arca_service.wscdc_descargar_comprobantes(
            session, tenant_id,
            comprobante.cuit_emisor,
            periodo
        )

        # Buscar el comprobante específico en el resultado
        for cbte in resultado:
            if (cbte.get("numero") == comprobante.numero and
                cbte.get("punto_venta") == comprobante.punto_venta):
                return {
                    "estado": EstadosComprobante.PRESENTE_VALIDO if cbte.get("cae") else EstadosComprobante.RECHAZADO_ARCA,
                    "detalle": cbte.get("estado", "Consultado vía WSCDC"),
                    "cae": cbte.get("cae"),
                    "fecha_emision": cbte.get("fecha_emision"),
                    "total": cbte.get("total")
                }

        # No encontrado en ARCA
        return {
            "estado": EstadosComprobante.AUSENTE,
            "detalle": "Comprobante no encontrado en ARCA",
            "cae": None
        }

    except Exception as e:
        logger.error(f"Error al consultar ARCA para comprobante {comprobante.id}: {e}")
        return None


# ============================================
# ALERTAS
# ============================================

async def _crear_alerta(
    session: AsyncSession,
    tenant_id: int,
    tipo: str,
    titulo: str,
    mensaje: str,
    comprobante_id: Optional[int] = None,
    severidad: str = "media"
):
    """
    Crear alerta en el sistema

    Args:
        session: Sesión de BD
        tenant_id: ID del tenant
        tipo: Tipo de alerta
        titulo: Título de la alerta
        mensaje: Mensaje detallado
        comprobante_id: ID del comprobante relacionado
        severidad: Nivel de severidad
    """
    alerta = Alerta(
        tenant_id=tenant_id,
        tipo=tipo,
        severidad=severidad,
        titulo=titulo,
        mensaje=mensaje,
        entidad_relacionada="comprobante",
        id_relacionado=comprobante_id,
        accion_requerida=f"Revisar {tipo}"
    )

    session.add(alerta)
    await session.commit()

    logger.info(f"Alerta creada: {tipo} - {titulo}")
