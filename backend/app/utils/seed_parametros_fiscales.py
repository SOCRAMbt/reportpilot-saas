"""
Seed de parámetros fiscales Monotributo 2026
Ejecutar una vez: python -m app.utils.seed_parametros_fiscales

⚠ VERIFICAR valores exactos según la RG ARCA vigente en 2026
"""
import asyncio
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PARAMETROS_2026 = {
    "monotributo_categorias_2026": {
        "vigencia_desde": date(2026, 1, 1),
        "vigencia_hasta": None,
        "valor": {
            "A": {"ingresos_brutos_anual": 2100000, "alquileres_anual": 350000, "precio_unitario_max": 0, "cuota_mensual": 15000},
            "B": {"ingresos_brutos_anual": 3150000, "alquileres_anual": 525000, "precio_unitario_max": 0, "cuota_mensual": 17000},
            "C": {"ingresos_brutos_anual": 4400000, "alquileres_anual": 733333, "precio_unitario_max": 0, "cuota_mensual": 20000},
            "D": {"ingresos_brutos_anual": 5500000, "alquileres_anual": 916667, "precio_unitario_max": 0, "cuota_mensual": 23000},
            "E": {"ingresos_brutos_anual": 6500000, "alquileres_anual": 1083333, "precio_unitario_max": 0, "cuota_mensual": 28000},
            "F": {"ingresos_brutos_anual": 7700000, "alquileres_anual": 1283333, "precio_unitario_max": 0, "cuota_mensual": 35000},
            "G": {"ingresos_brutos_anual": 9200000, "alquileres_anual": 1533333, "precio_unitario_max": 0, "cuota_mensual": 45000},
            "H": {"ingresos_brutos_anual": 10900000, "alquileres_anual": 1816667, "precio_unitario_max": 0, "cuota_mensual": 60000},
            "I": {"ingresos_brutos_anual": 13250000, "alquileres_anual": 2208333, "precio_unitario_max": 0, "cuota_mensual": 75000},
            "J": {"ingresos_brutos_anual": 16000000, "alquileres_anual": 2666667, "precio_unitario_max": 0, "cuota_mensual": 95000},
            "K": {"ingresos_brutos_anual": 20000000, "alquileres_anual": 3333333, "precio_unitario_max": 0, "cuota_mensual": 120000},
        },
        "descripcion": "Categorías Monotributo 2026 — servicios [VERIFICAR con RG ARCA vigente]",
        "fuente_normativa": "RG ARCA [VERIFICAR NÚMERO] / Ley 27.743"
    },
    "monotributo_cuotas_2026": {
        "vigencia_desde": date(2026, 1, 1),
        "vigencia_hasta": None,
        "valor": {
            "A": 15000, "B": 17000, "C": 20000, "D": 23000, "E": 28000,
            "F": 35000, "G": 45000, "H": 60000, "I": 75000, "J": 95000, "K": 120000
        },
        "descripcion": "Cuotas mensuales Monotributo 2026 [VERIFICAR]",
        "fuente_normativa": "RG ARCA [VERIFICAR NÚMERO]"
    },
    "monotributo_tope_maximo_anual": {
        "vigencia_desde": date(2026, 1, 1),
        "vigencia_hasta": None,
        "valor": 20000000,
        "descripcion": "Tope máximo anual Monotributo — exclusión inmediata",
        "fuente_normativa": "Ley 27.743"
    },
    "monotributo_precio_unitario_maximo": {
        "vigencia_desde": date(2026, 1, 1),
        "vigencia_hasta": None,
        "valor": 0,
        "descripcion": "Precio unitario máximo — 0 = sin tope configurado [VERIFICAR]",
        "fuente_normativa": "RG ARCA [VERIFICAR NÚMERO]"
    }
}


async def seed():
    """Insertar parámetros fiscales en la BD"""
    try:
        from app.db import AsyncSessionLocal
        from app.models import ParametroFiscal
        from sqlalchemy import select
    except ImportError:
        logger.error("No se pudo importar los módulos. ¿Está instalado el paquete?")
        return False

    async with AsyncSessionLocal() as session:
        creados = 0
        actualizados = 0

        for nombre, datos in PARAMETROS_2026.items():
            # Verificar si ya existe
            existente = await session.execute(
                select(ParametroFiscal).where(
                    ParametroFiscal.nombre == nombre,
                    ParametroFiscal.fecha_vigencia_desde == datos["vigencia_desde"]
                )
            )
            param = existente.scalar_one_or_none()

            if param:
                param.valor = datos["valor"]
                param.descripcion = datos.get("descripcion", "")
                param.fuente_normativa = datos.get("fuente_normativa", "")
                param.fecha_vigencia_hasta = datos.get("vigencia_hasta")
                actualizados += 1
                logger.info(f"  ✏️  Actualizado: {nombre}")
            else:
                param = ParametroFiscal(
                    nombre=nombre,
                    valor=datos["valor"],
                    descripcion=datos.get("descripcion", ""),
                    fuente_normativa=datos.get("fuente_normativa", ""),
                    fecha_vigencia_desde=datos["vigencia_desde"],
                    fecha_vigencia_hasta=datos.get("vigencia_hasta"),
                )
                session.add(param)
                creados += 1
                logger.info(f"  ✅ Creado: {nombre}")

        await session.commit()
        logger.info(f"\n✅ Seed completado: {creados} creados, {actualizados} actualizados")
        return True


# ============================================
# CALENDARIO FISCAL (seed)
# ============================================

VENCIMIENTOS_2026 = [
    # Monotributo - Vencimientos por terminación de CUIT
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 1, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 2, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 3, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 4, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 5, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 6, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 7, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 8, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 9, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 10, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 11, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "MONOTRIBUTO", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 12, 20), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},

    # IVA Mensual - RG 2026
    {"organismo": "ARCA", "tipo_obligacion": "IVA_MENSUAL", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 1, 17), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
    {"organismo": "ARCA", "tipo_obligacion": "IVA_MENSUAL", "terminacion_cuit": None, "categoria_monotributo": None,
     "fecha_base": date(2026, 2, 17), "es_prorroga": False, "fuente": "RG ARCA", "vigencia_desde": date(2026, 1, 1)},
]


async def seed_calendario_fiscal():
    """Insertar vencimientos fiscales en la BD"""
    try:
        from app.db import AsyncSessionLocal
        from app.models import CalendarioVencimiento
        from sqlalchemy import select
    except ImportError:
        logger.error("No se pudo importar los módulos para seed calendario")
        return 0

    async with AsyncSessionLocal() as session:
        creados = 0
        for venc in VENCIMIENTOS_2026:
            # Verificar duplicado
            existente = await session.execute(
                select(CalendarioVencimiento).where(
                    CalendarioVencimiento.organismo == venc["organismo"],
                    CalendarioVencimiento.tipo_obligacion == venc["tipo_obligacion"],
                    CalendarioVencimiento.fecha_base == venc["fecha_base"],
                )
            )
            if existente.scalar_one_or_none():
                continue

            cal = CalendarioVencimiento(
                organismo=venc["organismo"],
                tipo_obligacion=venc["tipo_obligacion"],
                terminacion_cuit=venc.get("terminacion_cuit"),
                categoria_monotributo=venc.get("categoria_monotributo"),
                fecha_base=venc["fecha_base"],
                fecha_efectiva=venc["fecha_base"],
                es_prorroga=venc.get("es_prorroga", False),
                fuente=venc.get("fuente", ""),
                vigencia_desde=venc["vigencia_desde"],
            )
            session.add(cal)
            creados += 1

        await session.commit()
        logger.info(f"✅ {creados} vencimientos fiscales cargados")
        return creados


if __name__ == "__main__":
    ok = asyncio.run(seed())
    if ok:
        asyncio.run(seed_calendario_fiscal())
    else:
        exit(1)
