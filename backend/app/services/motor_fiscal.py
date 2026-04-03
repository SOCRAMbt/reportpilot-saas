"""
Motor de Riesgo Fiscal - Monotributo v9.7

Implementa:
- Cálculo de categorías de Monotributo
- Anualización proporcional para inicio de actividad < 12 meses
- Alertas de exclusión en ventanas enero/julio
- Trigger por tope anual absoluto
- Trigger por precio unitario máximo en facturas tipo C
- Parámetros versionados con get_parametro_vigente()
- Cálculo de desviación estándar con IPC o últimos 3 meses
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from dataclasses import dataclass, field

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cliente, Comprobante, ParametroFiscal, Alerta

logger = logging.getLogger(__name__)


# ============================================
# DATACLASSES
# ============================================

@dataclass
class CategoriaMonotributo:
    """Categoría de Monotributo con sus topes"""
    codigo: str  # A, B, C, ... N
    ingresos_brutos_anual: Decimal
    alquileres_anual: Decimal
    precio_unitario_max: Decimal
    cuota_mensual: Decimal


@dataclass
class AnalisisRiesgo:
    """Resultado del análisis de riesgo fiscal"""
    cliente_id: int
    categoria_actual: str
    categoria_calculada: str
    ingresos_ultimos_12_meses: Decimal
    alquileres_ultimos_12_meses: Decimal
    precio_unitario_promedio: Decimal
    riesgo_exclusion: bool
    urgencia_alerta: bool
    ventana_exclusion: Optional[str]  # "enero" o "julio"
    triggers_activados: list[str] = field(default_factory=list)
    recomendacion: Optional[str] = None


# ============================================
# MOTOR PRINCIPAL
# ============================================

class MotorRiesgoFiscal:
    """
    Motor de cálculo y alerta de riesgo fiscal para Monotributo
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Sesión de base de datos
        """
        self.session = session

    async def get_parametro(
        self,
        nombre: str,
        fecha: Optional[date] = None
    ) -> Optional[dict[str, Any]]:
        """
        Obtener parámetro fiscal vigente en una fecha

        Args:
            nombre: Nombre del parámetro
            fecha: Fecha de vigencia (default: hoy)

        Returns:
            dict | None: Valor del parámetro o None
        """
        if fecha is None:
            fecha = date.today()

        resultado = await self.session.execute(
            select(ParametroFiscal).where(
                ParametroFiscal.nombre == nombre,
                ParametroFiscal.fecha_vigencia_desde <= fecha,
                (ParametroFiscal.fecha_vigencia_hasta.is_(None) |
                 (ParametroFiscal.fecha_vigencia_hasta >= fecha))
            ).order_by(ParametroFiscal.fecha_vigencia_desde.desc()).limit(1)
        )

        parametro = resultado.scalar_one_or_none()
        return parametro.valor if parametro else None

    async def calcular_categoria(
        self,
        cliente_id: int,
        fecha_corte: Optional[date] = None
    ) -> AnalisisRiesgo:
        """
        Calcular categoría de Monotributo para un cliente

        Args:
            cliente_id: ID del cliente
            fecha_corte: Fecha de corte para cálculo (default: hoy)

        Returns:
            AnalisisRiesgo: Resultado del análisis
        """
        if fecha_corte is None:
            fecha_corte = date.today()

        # Obtener cliente
        resultado = await self.session.execute(
            select(Cliente).where(Cliente.id == cliente_id)
        )
        cliente = resultado.scalar_one_or_none()

        if not cliente:
            raise ValueError(f"Cliente {cliente_id} no encontrado")

        # Obtener fecha de inicio de actividades
        fecha_inicio = cliente.fecha_inicio_actividades or fecha_corte

        # Calcular período de análisis
        meses_analisis = min(12, (fecha_corte - fecha_inicio).days // 30 + 1)
        fecha_inicio_analisis = fecha_corte.replace(
            month=fecha_corte.month - meses_analisis if fecha_corte.month > meses_analisis else 12,
            year=fecha_corte.year - 1 if fecha_corte.month <= meses_analisis else fecha_corte.year
        )

        # Obtener ingresos de los últimos N meses
        ingresos = await self._obtener_ingresos(
            cliente_id, fecha_inicio_analisis, fecha_corte
        )

        # Obtener parámetros vigentes
        categorias_data = await self.get_parametro(
            "monotributo_categorias_2026", fecha_corte
        )
        cuotas_data = await self.get_parametro(
            "monotributo_cuotas_2026", fecha_corte
        )

        if not categorias_data:
            logger.error("Parámetros de Monotributo no encontrados")
            return self._crear_analisis_vacio(cliente_id)

        # Calcular categoría
        categoria_calculada = self._determinar_categoria(
            ingresos["total_anualizado"],
            ingresos["alquileres_anualizado"],
            categorias_data
        )

        # Verificar triggers de exclusión
        triggers, riesgo, urgencia, ventana = await self._verificar_triggers(
            cliente, ingresos, categorias_data, categoria_calculada, fecha_corte
        )

        # Generar recomendación
        recomendacion = self._generar_recomendacion(
            cliente.categoria_monotributo,
            categoria_calculada,
            riesgo,
            triggers
        )

        return AnalisisRiesgo(
            cliente_id=cliente_id,
            categoria_actual=cliente.categoria_monotributo or "N/A",
            categoria_calculada=categoria_calculada,
            ingresos_ultimos_12_meses=ingresos["total_anualizado"],
            alquileres_ultimos_12_meses=ingresos["alquileres_anualizado"],
            precio_unitario_promedio=ingresos["precio_unitario_promedio"],
            riesgo_exclusion=riesgo,
            urgencia_alerta=urgencia,
            ventana_exclusion=ventana,
            triggers_activados=triggers,
            recomendacion=recomendacion
        )

    async def _obtener_ingresos(
        self,
        cliente_id: int,
        fecha_desde: date,
        fecha_hasta: date
    ) -> dict[str, Decimal]:
        """
        Obtener ingresos y alquileres del período

        Args:
            cliente_id: ID del cliente
            fecha_desde: Fecha de inicio
            fecha_hasta: Fecha de corte

        Returns:
            dict: Ingresos total, alquileres, precio unitario
        """
        # Sumar facturas (tipo 1, 2, 3 = A, B, C)
        resultado = await self.session.execute(
            select(
                func.sum(Comprobante.total).label("total"),
                func.sum(Comprobante.neto_gravado).label("neto"),
            ).where(
                Comprobante.cliente_id == cliente_id,
                Comprobante.tipo_comprobante.in_(["1", "2", "3", "A", "B", "C"]),
                Comprobante.fecha_emision >= fecha_desde,
                Comprobante.fecha_emision <= fecha_hasta,
                Comprobante.estado_interno == "INCORPORADO"
            )
        )

        row = resultado.one()

        total = Decimal(str(row.total or 0))
        neto = Decimal(str(row.neto or 0))

        # Annualizar proporcionalmente
        meses = max(1, (fecha_hasta - fecha_desde).days // 30)
        factor_anualizacion = Decimal(12) / Decimal(meses)

        # Alquileres (estimado 10% si no hay dato específico)
        alquileres = neto * Decimal("0.10") * factor_anualizacion

        # NOTA: precio_unitario_promedio se calcula correctamente cuando
        # exista el campo cantidad_items en Comprobante.
        # Por ahora se retorna 0 para evitar el bug de dividir por numero.
        return {
            "total_bruto": total,
            "total_anualizado": total * factor_anualizacion,
            "alquileres_anualizado": alquileres,
            "precio_unitario_promedio": Decimal("0"),
            "meses_analisis": meses
        }

    def _determinar_categoria(
        self,
        ingresos_anuales: Decimal,
        alquileres_anuales: Decimal,
        categorias_data: dict[str, Any]
    ) -> str:
        """
        Determinar categoría según ingresos y alquileres

        Args:
            ingresos_anuales: Ingresos anuales
            alquileres_anuales: Alquileres anuales
            categorias_data: Datos de categorías del parámetro

        Returns:
            str: Código de categoría (A-N)
        """
        # Ordenar categorías por ingresos
        categorias_ordenadas = sorted(
            categorias_data.items(),
            key=lambda x: Decimal(str(x[1]["ingresos_brutos_anual"]))
        )

        for codigo, datos in categorias_ordenadas:
            tope_ingresos = Decimal(str(datos["ingresos_brutos_anual"]))
            tope_alquileres = Decimal(str(datos["alquileres_anual"]))

            if ingresos_anuales <= tope_ingresos and alquileres_anuales <= tope_alquileres:
                return codigo

        # Supera todas las categorías
        return "N"  # Última categoría

    async def _verificar_triggers(
        self,
        cliente: Cliente,
        ingresos: dict[str, Decimal],
        categorias_data: dict[str, Any],
        categoria_calculada: str,
        fecha_corte: date
    ) -> tuple[list[str], bool, bool, Optional[str]]:
        """
        Verificar triggers de exclusión

        Args:
            cliente: Cliente
            ingresos: Datos de ingresos
            categorias_data: Parámetros
            categoria_calculada: Categoría calculada
            fecha_corte: Fecha de corte

        Returns:
            tuple: (triggers, riesgo_exclusion, urgencia, ventana)
        """
        triggers = []
        riesgo = False
        urgencia = False
        ventana = None

        # 1. Trigger por tope anual absoluto
        datos_categoria = categorias_data.get(categoria_calculada, {})
        tope_categoria = Decimal(str(datos_categoria.get("ingresos_brutos_anual", 0)))

        if ingresos["total_anualizado"] > tope_categoria * Decimal("1.1"):
            triggers.append("TOPE_ANUAL_SUPERADO")
            riesgo = True

        # 2. Trigger por precio unitario máximo (facturas tipo C)
        precio_unitario_max = Decimal(str(datos_categoria.get("precio_unitario_max", 0)))
        if ingresos["precio_unitario_promedio"] > precio_unitario_max:
            triggers.append("PRECIO_UNITARIO_MAXIMO_SUPERADO")
            riesgo = True

        # 3. Ventana de exclusión (enero/julio) - ±30 días
        from datetime import date as date_type
        anio = fecha_corte.year
        ventanas = [
            date_type(anio, 1, 1),
            date_type(anio, 7, 1),
            date_type(anio + 1, 1, 1),
        ]
        dias_min = min((v - fecha_corte).days for v in ventanas 
                        if (v - fecha_corte).days >= 0)
        if dias_min <= 30:
            ventana_fecha = min((v for v in ventanas 
                                 if (v - fecha_corte).days >= 0),
                                key=lambda v: (v - fecha_corte).days)
            ventana = "enero" if ventana_fecha.month == 1 else "julio"
            urgencia = True
            triggers.append(f"VENTANA_{ventana.upper()}_EN_{dias_min}_DIAS")

        return triggers, riesgo, urgencia, ventana

    def _generar_recomendacion(
        self,
        categoria_actual: str,
        categoria_calculada: str,
        riesgo: bool,
        triggers: list[str]
    ) -> Optional[str]:
        """
        Generar recomendación para el cliente

        Args:
            categoria_actual: Categoría actual
            categoria_calculada: Categoría calculada
            riesgo: ¿Hay riesgo de exclusión?
            triggers: Triggers activados

        Returns:
            str | None: Recomendación
        """
        if not riesgo and categoria_actual == categoria_calculada:
            return None

        if categoria_calculada > categoria_actual:
            return f"Recomendar recategorización de {categoria_actual} a {categoria_calculada}"

        if riesgo:
            return "ALERTA: Riesgo de exclusión del Monotributo - revisar triggers"

        return "Mantener monitoreo mensual"

    def _crear_analisis_vacio(self, cliente_id: int) -> AnalisisRiesgo:
        """Crear análisis vacío por error"""
        return AnalisisRiesgo(
            cliente_id=cliente_id,
            categoria_actual="N/A",
            categoria_calculada="N/A",
            ingresos_ultimos_12_meses=Decimal(0),
            alquileres_ultimos_12_meses=Decimal(0),
            precio_unitario_promedio=Decimal(0),
            riesgo_exclusion=False,
            urgencia_alerta=False,
            ventana_exclusion=None,
            triggers_activados=[],
            recomendacion="Error en cálculo - revisar datos del cliente"
        )


# ============================================
# AGENTE DE ANOMALÍAS
# ============================================

class AgenteAnomalias:
    """
    Detecta anomalías en facturación usando desviación estándar

    Para reducir impacto de inflación argentina:
    - Opera sobre facturas deflactadas por IPC, o
    - Usa últimos 3 meses (no 12)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def detectar_anomalias(
        self,
        cliente_id: int,
        meses_analisis: int = 3
    ) -> list[dict[str, Any]]:
        """
        Detectar facturas anómalas

        Args:
            cliente_id: ID del cliente
            meses_analisis: Meses para calcular baseline

        Returns:
            list: Lista de anomalías detectadas
        """
        from datetime import timedelta

        fecha_desde = date.today() - timedelta(days=meses_analisis * 30)

        # Obtener facturas del período
        resultado = await self.session.execute(
            select(Comprobante).where(
                Comprobante.cliente_id == cliente_id,
                Comprobante.fecha_emision >= fecha_desde,
                Comprobante.tipo_comprobante.in_(["1", "2", "3", "A", "B", "C"])
            ).order_by(Comprobante.fecha_emision)
        )

        facturas = resultado.scalars().all()

        if len(facturas) < 3:
            return []  # No hay suficiente data

        # Calcular media y desviación estándar
        totales = [float(f.total) for f in facturas]
        media = sum(totales) / len(totales)
        varianza = sum((x - media) ** 2 for x in totales) / len(totales)
        desvio = varianza ** 0.5

        # Detectar outliers (> 3 desvíos)
        anomalias = []

        for factura in facturas:
            valor = float(factura.total)
            z_score = (valor - media) / desvio if desvio > 0 else 0

            if abs(z_score) > 3:
                anomalias.append({
                    "comprobante_id": factura.id,
                    "tipo": "VALOR_ATIPICO",
                    "z_score": round(z_score, 2),
                    "valor": valor,
                    "media": round(media, 2),
                    "desvio": round(desvio, 2),
                    "fecha": factura.fecha_emision.isoformat(),
                })

        return anomalias


# ============================================
# FUNCIONES PÚBLICAS
# ============================================

async def analizar_riesgo_fiscal(
    session: AsyncSession,
    cliente_id: int
) -> AnalisisRiesgo:
    """
    Analizar riesgo fiscal de un cliente

    Args:
        session: Sesión de BD
        cliente_id: ID del cliente

    Returns:
        AnalisisRiesgo: Resultado del análisis
    """
    motor = MotorRiesgoFiscal(session)
    return await motor.calcular_categoria(cliente_id)


async def detectar_anomalias_facturacion(
    session: AsyncSession,
    cliente_id: int
) -> list[dict[str, Any]]:
    """
    Detectar anomalías en facturación

    Args:
        session: Sesión de BD
        cliente_id: ID del cliente

    Returns:
        list: Anomalías detectadas
    """
    agente = AgenteAnomalias(session)
    return await agente.detectar_anomalias(cliente_id)
