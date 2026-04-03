"""
Script de verificación pre-producción.
Ejecutar antes del primer cliente real.

    python -m app.utils.health_check
"""
import asyncio
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def verificar_todo() -> bool:
    errores = []
    warnings = []

    print("\n🔍 Verificando AccountantOS...\n")

    # 1. BD operativa
    try:
        from app.db import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        print("  ✅ Base de datos conectada")
    except Exception as e:
        errores.append(f"BD: {e}")
        print(f"  ❌ Base de datos: {e}")

    # 2. Redis operativo
    try:
        import redis
        from app.core.config import settings
        r = redis.from_url(settings.redis_url)
        r.ping()
        print("  ✅ Redis conectado")
        # Verificar persistencia
        aof = r.config_get("appendonly")
        if aof.get("appendonly") == "yes":
            warnings.append("Redis tiene AOF habilitado — los tokens WSAA persisten a disco")
            print("  ⚠️  Redis AOF habilitado — desactivar para tokens WSAA")
        else:
            print("  ✅ Redis sin persistencia AOF (correcto para tokens WSAA)")
        r.close()
    except Exception as e:
        warnings.append(f"Redis no disponible (puede ser modo dev): {e}")
        print(f"  ⚠️  Redis no disponible: {e}")

    # 3. Certificado ARCA
    try:
        from app.core.config import settings
        cert_path = Path(settings.arca_cert_path)
        key_path = Path(settings.arca_key_path)
        if cert_path.exists() and key_path.exists():
            print("  ✅ Certificado ARCA encontrado")
        else:
            warnings.append("Certificado ARCA no configurado — ir a Configuración → ARCA")
            print("  ⚠️  Certificado ARCA no encontrado (configurar desde UI)")
    except Exception as e:
        warnings.append(f"No se pudo verificar certificado: {e}")
        print(f"  ⚠️  Certificado ARCA: {e}")

    # 4. Parámetros fiscales en BD
    try:
        from app.db import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as s:
            r = await s.execute(text("SELECT COUNT(*) FROM parametros_fiscales"))
            count = r.scalar()
            if count == 0:
                warnings.append("Parámetros fiscales vacíos — ejecutar seed_parametros_fiscales.py")
                print("  ⚠️  Parámetros fiscales vacíos")
            else:
                print(f"  ✅ {count} parámetros fiscales cargados")
    except Exception as e:
        warnings.append(f"No se pudo verificar parámetros fiscales: {e}")
        print(f"  ⚠️  Parámetros fiscales: {e}")

    # 5. Celery importable
    try:
        from app.workers.celery_app import celery_app
        print("  ✅ Celery importable (sin syntax errors)")
    except Exception as e:
        errores.append(f"Celery: {e}")
        print(f"  ❌ Celery: {e}")

    # 6. Modelos importables
    try:
        from app.models import (
            Tenant, Usuario, Cliente, Comprobante, ParametroFiscal,
            VEP, Alerta, WSAAToken, RelacionARCA, LogAuditoria,
            SolicitudARCO, CalendarioVencimiento
        )
        print("  ✅ Todos los modelos importables (12)")
    except Exception as e:
        errores.append(f"Modelos: {e}")
        print(f"  ❌ Modelos: {e}")

    # 7. HMAC-SHA256 verificación
    try:
        from app.core.security import tokenizar_cuit
        t1 = tokenizar_cuit("20123456789", 1)
        t2 = tokenizar_cuit("20123456789", 2)
        if t1 != t2:
            print("  ✅ HMAC-SHA256 por tenant funcionando")
        else:
            errores.append("HMAC: mismo hash para diferentes tenants")
            print("  ❌ HMAC: mismo hash para diferentes tenants")
    except Exception as e:
        errores.append(f"HMAC: {e}")
        print(f"  ❌ HMAC: {e}")

    # Resumen
    print()
    if errores:
        print(f"❌ {len(errores)} ERRORES CRÍTICOS — NO iniciar con clientes reales:")
        for e in errores:
            print(f"   • {e}")
    if warnings:
        print(f"⚠️  {len(warnings)} ADVERTENCIAS:")
        for w in warnings:
            print(f"   • {w}")
    if not errores:
        print("🟢 Sistema listo para arrancar.\n")

    return len(errores) == 0


if __name__ == "__main__":
    ok = asyncio.run(verificar_todo())
    sys.exit(0 if ok else 1)
