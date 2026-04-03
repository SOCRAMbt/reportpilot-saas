"""
Tareas Celery para operaciones de ARCA/AFIP
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import select, delete

from app.db import AsyncSessionLocal
from app.models import WSAAToken, Comprobante, Cliente, Tenant
from app.services.arca import ARCAService
from app.services.delta_processing import (
    EstadosComprobante, procesar_delta_comprobante, calcular_hash_delta
)

logger = logging.getLogger(__name__)

arca_service = ARCAService()


@shared_task(bind=True, max_retries=3)
def descargar_comprobantes_nocturno(self):
    """
    Descarga masiva de comprobantes (02:00-05:00)

    Se ejecuta durante la ventana nocturna cuando ARCA tiene menor carga.
    Descarga comprobantes del mes anterior para todos los tenants activos.
    """
    logger.info("Iniciando descarga masiva nocturna")

    async def run_descarga():
        async with AsyncSessionLocal() as session:
            # Obtener todos los tenants activos
            resultado = await session.execute(
                select(Tenant).where(Tenant.activo == True)
            )
            tenants = resultado.scalars().all()

            logger.info(f"Tenants activos: {len(tenants)}")

            # Calcular período a descargar (mes anterior)
            ahora = datetime.now()
            if ahora.month == 1:
                anio_anterior = ahora.year - 1
                mes_anterior = 12
            else:
                anio_anterior = ahora.year
                mes_anterior = ahora.month - 1

            periodo = (anio_anterior, mes_anterior)
            logger.info(f"Descargando período: {periodo[0]}-{periodo[1]:02d}")

            total_descargados = 0
            total_errores = 0

            for tenant in tenants:
                try:
                    logger.info(f"Descargando para tenant {tenant.id} ({tenant.nombre})")

                    # Obtener CUITs de clientes asociados al tenant
                    clientes_result = await session.execute(
                        select(Cliente).where(
                            Cliente.tenant_id == tenant.id,
                            Cliente.activo == True
                        )
                    )
                    clientes = clientes_result.scalars().all()

                    # Para cada cliente, descargar comprobantes emitidos
                    for cliente in clientes:
                        try:
                            comprobantes = await arca_service.wscdc_descargar_comprobantes(
                                session,
                                tenant.id,
                                cliente.cuit,
                                periodo
                            )

                            logger.info(f"  CUIT {cliente.cuit}: {len(comprobantes)} comprobantes")

                            # Procesar cada comprobante con delta-processing
                            for cbte in comprobantes:
                                try:
                                    # Determinar estado según datos de ARCA
                                    estado_arca = determinar_estado_arca(cbte)

                                    # Calcular hash_delta ANTES de crear el comprobante
                                    hash_delta = calcular_hash_delta(
                                        str(cbte.get("cuit_emisor", cliente.cuit)),
                                        int(cbte.get("punto_venta", 0)),
                                        int(cbte.get("numero", 0))
                                    )

                                    # Ejecutar delta-processing
                                    estado_interno, observaciones = await procesar_delta_comprobante(
                                        session,
                                        tenant.id,
                                        {
                                            "cuit_emisor": cbte.get("cuit_emisor", cliente.cuit),
                                            "punto_venta": cbte.get("punto_venta"),
                                            "numero": cbte.get("numero"),
                                            "tipo_comprobante": cbte.get("tipo_comprobante"),
                                            "total": float(cbte.get("total", 0)),
                                            "fecha_emision": cbte.get("fecha_emision"),
                                        },
                                        estado_arca
                                    )

                                    # Si es nuevo (no duplicado), crear comprobante
                                    if estado_interno != EstadosComprobante.ANULADO:
                                        nuevo_comprobante = Comprobante(
                                            tenant_id=tenant.id,
                                            cliente_id=cliente.id,
                                            tipo_comprobante=cbte.get("tipo_comprobante"),
                                            punto_venta=cbte.get("punto_venta"),
                                            numero=cbte.get("numero"),
                                            cuit_emisor=cbte.get("cuit_emisor", cliente.cuit),
                                            fecha_emision=cbte.get("fecha_emision"),
                                            total=cbte.get("total", 0),
                                            neto_gravado=cbte.get("neto_gravado", 0),
                                            iva=cbte.get("iva", 0),
                                            cae=cbte.get("cae"),
                                            estado_arca=estado_arca,
                                            estado_interno=estado_interno,
                                            origen="ws_cdc",
                                            observaciones=observaciones,
                                            hash_delta=hash_delta,
                                            metadata={"descarga_nocturna": True}
                                        )
                                        session.add(nuevo_comprobante)
                                        total_descargados += 1

                                except Exception as e:
                                    logger.error(f"Error procesando comprobante: {e}")
                                    total_errores += 1

                        except Exception as e:
                            logger.error(f"Error descargando CUIT {cliente.cuit}: {e}")
                            total_errores += 1

                    await session.commit()

                except Exception as e:
                    logger.error(f"Error procesando tenant {tenant.id}: {e}")
                    await session.rollback()
                    total_errores += 1

            logger.info(f"Descarga nocturna completada: {total_descargados} comprobantes, {total_errores} errores")
            return total_descargados, total_errores

    import asyncio
    try:
        return asyncio.run(run_descarga())
    except Exception as e:
        logger.error(f"Error en descarga nocturna: {e}")
        raise self.retry(exc=e, countdown=300)


def determinar_estado_arca(cbte: dict) -> str:
    """
    Determinar estado ARCA según datos del comprobante

    Args:
        cbte: Datos del comprobante

    Returns:
        str: Estado ARCA
    """
    if cbte.get("cae") and cbte.get("estado") == "V":
        return EstadosComprobante.PRESENTE_VALIDO
    elif cbte.get("estado") == "A":
        return EstadosComprobante.PRESENTE_ANULADO
    elif cbte.get("estado") == "R":
        return EstadosComprobante.RECHAZADO_ARCA
    elif not cbte.get("cae"):
        return EstadosComprobante.AUSENTE
    else:
        return EstadosComprobante.PRESENTE_VALIDO


@shared_task(bind=True, max_retries=3)
def ejecutar_re_verificaciones(self):
    """
    Ejecutar re-verificaciones T+7 y T+30
    """
    logger.info("Iniciando re-verificaciones")

    from app.services.delta_processing import ejecutar_re_verificaciones as re_verificar

    async def run():
        async with AsyncSessionLocal() as session:
            await re_verificar(session)

    # Ejecutar en evento loop
    import asyncio
    asyncio.run(run())

    logger.info("Re-verificaciones completadas")


@shared_task(bind=True)
def consultar_estado_arca(self, comprobante_id: int, tenant_id: int):
    """
    Consultar estado de comprobante en ARCA
    """
    async def consultar():
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                select(Comprobante).where(Comprobante.id == comprobante_id)
            )
            comprobante = resultado.scalar_one_or_none()

            if not comprobante:
                logger.warning(f"Comprobante {comprobante_id} no encontrado")
                return

            # Consultar estado real en ARCA
            from app.services.delta_processing import _consultar_estado_en_arca
            from app.services.arca import ARCAService

            arca_service = ARCAService()
            estado = await _consultar_estado_en_arca(
                arca_service, session, tenant_id, comprobante
            )

            if estado:
                comprobante.estado_arca = estado["estado"]
                comprobante.estado_arca_detalle = estado.get("detalle", "")
                comprobante.fecha_consulta_arca = datetime.now()
                await session.commit()
                logger.info(f"Estado ARCA actualizado para comprobante {comprobante_id}")
            else:
                logger.warning(f"No se pudo obtener estado ARCA para comprobante {comprobante_id}")

    import asyncio
    try:
        asyncio.run(consultar())
    except Exception as e:
        logger.error(f"Error consultando ARCA: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def limpieza_tokens_wsaa():
    """
    Limpiar tokens WSAA expirados de la BD
    """
    async def limpiar():
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                delete(WSAAToken).where(
                    WSAAToken.vencimiento < datetime.now()
                )
            )
            eliminados = resultado.rowcount
            await session.commit()
            logger.info(f"Limpieza WSAA: {eliminados} tokens eliminados")

    import asyncio
    asyncio.run(limpiar())


@shared_task(bind=True, max_retries=5)
def sincronizar_comprobante_arca(self, comprobante_id: int):
    """
    Sincronizar comprobante con ARCA (delta-processing)
    """
    async def sincronizar():
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                select(Comprobante).where(Comprobante.id == comprobante_id)
            )
            comprobante = resultado.scalar_one_or_none()

            if not comprobante:
                return

            # Consultar estado REAL en ARCA primero
            from app.services.delta_processing import _consultar_estado_en_arca
            from app.services.arca import ARCAService

            arca_service = ARCAService()
            estado_arca = await _consultar_estado_en_arca(
                arca_service, session, comprobante.tenant_id, comprobante
            )

            if not estado_arca:
                logger.warning(f"No se pudo obtener estado ARCA para comprobante {comprobante_id}")
                return

            # Procesar delta con el estado real obtenido
            from app.services.delta_processing import procesar_delta_comprobante

            estado, observaciones = await procesar_delta_comprobante(
                session,
                comprobante.tenant_id,
                {
                    "cuit_emisor": comprobante.cuit_emisor,
                    "punto_venta": comprobante.punto_venta,
                    "numero": comprobante.numero,
                    "tipo_comprobante": comprobante.tipo_comprobante,
                    "total": float(comprobante.total),
                    "fecha_emision": comprobante.fecha_emision.isoformat() if comprobante.fecha_emision else None,
                },
                estado_arca["estado"]
            )

            comprobante.estado_interno = estado
            if observaciones:
                comprobante.observaciones = observaciones

            await session.commit()

    import asyncio
    try:
        asyncio.run(sincronizar())
    except Exception as e:
        logger.error(f"Error sincronizando: {e}")
        raise self.retry(exc=e, countdown=600)
