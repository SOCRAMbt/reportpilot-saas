"""
Tareas Celery para operaciones fiscales
"""

import logging
from datetime import date, timedelta
from celery import shared_task
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Cliente, VEP, Alerta
from app.services.motor_fiscal import MotorRiesgoFiscal, AgenteAnomalias

logger = logging.getLogger(__name__)


@shared_task
def pre_liquidar_veps_mes():
    """
    Pre-liquidar VEPs del mes siguiente

    Se ejecuta días 13, 21, 23 para tener borradores listos
    antes del vencimiento (día 20 para monotributo)
    """
    logger.info("Pre-liquidando VEPs del mes siguiente")

    async def pre_liquidar():
        async with AsyncSessionLocal() as session:
            # Obtener todos los clientes activos
            resultado = await session.execute(
                select(Cliente).where(Cliente.activo == True)
            )
            clientes = resultado.scalars().all()

            mes_siguiente = date.today().month + 1
            anio = date.today().year
            if mes_siguiente > 12:
                mes_siguiente = 1
                anio += 1

            periodo = f"{anio}-{mes_siguiente:02d}"

            for cliente in clientes:
                # Verificar si ya existe VEP para este período
                existe = await session.execute(
                    select(VEP).where(
                        VEP.cliente_id == cliente.id,
                        VEP.periodo == periodo
                    )
                )

                if existe.scalar_one_or_none():
                    continue  # Ya existe

                # Calcular categoría actual
                motor = MotorRiesgoFiscal(session)
                analisis = await motor.calcular_categoria(cliente.id)

                # Crear VEP pre-liquidado
                vep = VEP(
                    tenant_id=cliente.tenant_id,
                    cliente_id=cliente.id,
                    tipo_vep="monotributo",
                    periodo=periodo,
                    categoria=analisis.categoria_calculada,
                    importe_original=0,  # Se calcula según tabla
                    intereses=0,
                    importe_total=0,
                    estado="PRE_LIQUIDADO",
                )

                session.add(vep)

            await session.commit()
            logger.info(f"VEPs pre-liquidados: {len(clientes)} clientes")

    import asyncio
    asyncio.run(pre_liquidar())


@shared_task
def analizar_riesgo_fiscal_cartera():
    """
    Analizar riesgo fiscal de toda la cartera de clientes
    """
    logger.info("Analizando riesgo fiscal de cartera")

    async def analizar():
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                select(Cliente).where(Cliente.activo == True)
            )
            clientes = resultado.scalars().all()

            alertas_creadas = 0

            for cliente in clientes:
                motor = MotorRiesgoFiscal(session)
                analisis = await motor.calcular_categoria(cliente.id)

                if analisis.riesgo_exclusion:
                    # Crear alerta
                    alerta = Alerta(
                        tenant_id=cliente.tenant_id,
                        cliente_id=cliente.id,
                        tipo="riesgo_fiscal",
                        severidad="alta" if analisis.urgencia_alerta else "media",
                        titulo=f"Riesgo fiscal - {cliente.razon_social}",
                        mensaje=analisis.recomendacion or "Revisar situación fiscal",
                        accion_requerida=analisis.recomendacion,
                    )
                    session.add(alerta)
                    alertas_creadas += 1

            await session.commit()
            logger.info(f"Alertas de riesgo creadas: {alertas_creadas}")

    import asyncio
    asyncio.run(analizar())


@shared_task
def detectar_anomalias_cartera():
    """
    Detectar anomalías en facturación de toda la cartera
    """
    logger.info("Detectando anomalías en cartera")

    async def detectar():
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                select(Cliente).where(Cliente.activo == True)
            )
            clientes = resultado.scalars().all()

            anomalias_detectadas = 0

            for cliente in clientes:
                agente = AgenteAnomalias(session)
                anomalias = await agente.detectar_anomalias(cliente.id)

                for anomalia in anomalias:
                    alerta = Alerta(
                        tenant_id=cliente.tenant_id,
                        cliente_id=cliente.id,
                        tipo="anomalia_facturacion",
                        severidad="media",
                        titulo=f"Anomalía detectada - {cliente.razon_social}",
                        mensaje=f"Factura atípica detectada (z-score: {anomalia['z_score']})",
                        entidad_relacionada="comprobante",
                        id_relacionado=anomalia["comprobante_id"],
                    )
                    session.add(alerta)
                    anomalias_detectadas += 1

            await session.commit()
            logger.info(f"Anomalías detectadas: {anomalias_detectadas}")

    import asyncio
    asyncio.run(detectar())
