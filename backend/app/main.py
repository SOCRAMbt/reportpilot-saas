"""
AccountantOS v9.7 - Aplicación Principal FastAPI
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api import auth, comprobantes, veps, clientes, dashboard, bank_kit, alertas, configuracion, arco
from app.db import async_engine

# ============================================
# CONFIGURACIÓN DE LOGGING
# ============================================

# Configurar structlog para logging estructurado
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory()
)

logger = structlog.get_logger()


# ============================================
# LIFESPAN - Startup y Shutdown
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejar startup y shutdown de la aplicación
    """
    # Startup
    logger.info("Iniciando AccountantOS", version="9.7.0")

    # Verificar conexión a BD
    try:
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Conexión a BD verificada")
    except Exception as e:
        logger.error("Error conectando a BD", error=str(e))

    # Verificar Redis (solo si está habilitado)
    if settings.redis_enabled:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            logger.info("Conexión a Redis verificada")
            await redis_client.close()
        except Exception as e:
            logger.error("Error conectando a Redis", error=str(e))
    else:
        logger.info("Redis deshabilitado - usando modo desarrollo")

    yield

    # Shutdown
    logger.info("Cerrando AccountantOS")
    await async_engine.dispose()


# ============================================
# APLICACIÓN FASTAPI
# ============================================

app = FastAPI(
    title="AccountantOS API",
    description="Sistema de Automatización Contable para Argentina v9.7",
    version="9.7.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ============================================
# MIDDLEWARE
# ============================================

# CORS - Permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Endpoint raíz - health check básico"""
    return {
        "nombre": "AccountantOS API",
        "version": "9.7.0",
        "estado": "ok"
    }


@app.get("/health")
async def health_check():
    """Health check completo"""
    health = {
        "api": "ok",
        "version": "9.7.0"
    }

    # Verificar BD
    try:
        from sqlalchemy import select
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
        health["database"] = "ok"
    except Exception as e:
        health["database"] = f"error: {str(e)}"

    # Verificar Redis (solo si está habilitado)
    if settings.redis_enabled:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            await redis_client.close()
            health["redis"] = "ok"
        except Exception as e:
            health["redis"] = f"error: {str(e)}"
    else:
        health["redis"] = "disabled"

    return health


# Registrar routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(comprobantes.router, prefix="/api/v1")
app.include_router(veps.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(bank_kit.router, prefix="/api/v1")
app.include_router(alertas.router, prefix="/api/v1")
app.include_router(configuracion.router, prefix="/api/v1")
app.include_router(arco.router, prefix="/api/v1")


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
