"""
Monitor de Monotributo — Comparación de facturación acumulada vs categorías ARCA

Analiza continuamente la situación de cada cliente monotributista para detectar
riesgo de exclusión del régimen antes de que ocurra.

Compara la facturación de los últimos 12 meses contra los topes de categoría
(A a K) vigentes según los parámetros fiscales cargados en el sistema.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cliente, Comprobante, ParametroFiscal, Alerta
from app.services.motor_fiscal import MotorRiesgoFiscal

logger = logging.getLogger(__name__)


class MonitorMonotributo:
    """
    Monitorea la facturación de clientes monotributistas y genera alertas
    cuando se acercan a los topes de su categoría o deberían recategorizarse.
    """

    def __init__(self, session: AsyncSession, tenant_id: int = 1):
        self.session = session
        self.tenant_id = tenant_id

    async def analizar_todos(self) -> dict:
        """
        Analiza TODOS los clientes monotributistas del tenant.

        Retorna:
            dict con resumen: {"analizados": N, "alertas_creadas": N, "riesgo_alto": N}
        """
        resultado = await self.session.execute(
            select(Cliente).where(
                Cliente.tenant_id == self.tenant_id,
                Cliente.activo == True,
                Cliente.tipo_responsable.ilike("%monotributo%"),
            )
        )
        clientes = resultado.scalars().all()

        stats = {"analizados": 0, "alertas_creadas": 0, "riesgo_alto": 0, "riesgo_medio": 0}

        for cliente in clientes:
            analisis = await self._analizar_cliente(cliente)
            if analisis:
                stats["alertas_creadas"] += 1
                if analisis.get("urgente"):
                    stats["riesgo_alto"] += 1
                else:
                    stats["riesgo_medio"] += 1
            stats["analizados"] += 1

        if stats["analizados"] > 0:
            logger.info(
                f"Monitor Monotributo: {stats['analizados']} clientes analizados, "
                f"{stats['alertas_creadas']} alertas creadas "
                f"({stats['riesgo_alto']} alto, {stats['riesgo_medio']} medio)"
            )

        return stats

    async def _analizar_cliente(self, cliente: Cliente) -> Optional[dict]:
        """
        Analiza un cliente monotributista individual.

        Retorna dict con info de alerta si hay riesgo, None si está al día.
        """
        motor = MotorRiesgoFiscal(self.session)

        try:
            analisis = await motor.calcular_categoria(cliente.id)
        except Exception as e:
            logger.error(f"Error analizando cliente {cliente.id}: {e}")
            return None

        if not analisis.riesgo_exclusion and analisis.categoria_actual == analisis.categoria_calculada:
            return None  # Cliente al día

        # Crear alerta apropiada
        severidad = "critica" if analisis.riesgo_exclusion else "alta"
        titulo = f"Monotributo: {cliente.razon_social}"

        if analisis.riesgo_exclusion:
            mensaje = (
                f"⚠️ RIESGO DE EXCLUSIÓN — Facturación proyectada supera el tope "
                f"de categoría {analisis.categoria_calculada}. "
                f"Facturación actual: ${analisis.ingresos_ultimos_12_meses:,.2f}"
            )
        else:
            mensaje = (
                f"Recategorización recomendada de {analisis.categoria_actual} "
                f"a {analisis.categoria_calculada}. "
                f"Facturación: ${analisis.ingresos_ultimos_12_meses:,.2f}"
            )

        if analisis.ventana_exclusion:
            mensaje += f" — Ventana de {analisis.ventana_exclusion} próxima."

        alerta = Alerta(
            tenant_id=self.tenant_id,
            cliente_id=cliente.id,
            tipo="riesgo_monotributo",
            severidad=severidad,
            titulo=titulo,
            mensaje=mensaje,
            accion_requerida=analisis.recomendacion or "Revisar situación fiscal del cliente",
        )
        self.session.add(alerta)
        await self.session.commit()

        return {"urgente": analisis.riesgo_exclusion, "categoria_calculada": analisis.categoria_calculada}


async def ejecutar_monitor_monotributo(session: AsyncSession, tenant_id: int = 1) -> dict:
    """
    Función de conveniencia para ejecutar el monitor desde Celery o scripts.
    """
    monitor = MonitorMonotributo(session, tenant_id)
    return await monitor.analizar_todos()
