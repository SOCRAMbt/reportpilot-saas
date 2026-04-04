"""
AccountantOS v9.7 - Aplicación Principal FastAPI
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import verify_access_token
from app.core.context import current_tenant_id
from app.api import auth, comprobantes, veps, clientes, dashboard, bank_kit, alertas, configuracion, arco, calendario, ingesta
from app.api.webhooks import whatsapp
from app.db import async_engine

# ============================================
# CONFIGURACIÓN DE LOGGING
# ============================================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("accountantos")


# ============================================
# LIFESPAN - Startup y Shutdown
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejar startup y shutdown de la aplicación"""
    logger.info("Iniciando AccountantOS v9.7")

    try:
        from sqlalchemy import text
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Conexión a BD verificada")
    except Exception as e:
        logger.error("Error conectando a BD: %s", e)

    if settings.redis_enabled:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            logger.info("Conexión a Redis verificada")
            await redis_client.close()
        except Exception as e:
            logger.error("Error conectando a Redis: %s", e)
    else:
        logger.info("Redis deshabilitado - modo desarrollo")

    yield

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
    lifespan=lifespan,
)

# ============================================
# MIDDLEWARE
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# MIDDLEWARE — RLS: setear tenant_id en cada request
# ============================================

class TenantRLSMiddleware(BaseHTTPMiddleware):
    """
    Extrae tenant_id del JWT y lo guarda en el contexto del request.
    get_db() lo lee y ejecuta set_config('app.current_tenant', ...)
    para activar Row-Level Security en PostgreSQL.
    """

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = verify_access_token(token)
                if payload and payload.get("tenant_id"):
                    tid = int(payload["tenant_id"])
                    current_tenant_id.set(tid)
            except Exception:
                pass  # Si el token es inválido, el endpoint lo rechazará

        return await call_next(request)


app.add_middleware(TenantRLSMiddleware)


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {"nombre": "AccountantOS API", "version": "9.7.0", "estado": "ok"}


@app.get("/health")
async def health_check():
    health = {"api": "ok", "version": "9.7.0"}

    try:
        from sqlalchemy import select
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
        health["database"] = "ok"
    except Exception as e:
        health["database"] = f"error: {e}"

    if settings.redis_enabled:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            await redis_client.close()
            health["redis"] = "ok"
        except Exception as e:
            health["redis"] = f"error: {e}"
    else:
        health["redis"] = "disabled"

    return health


# ============================================
# ROUTERS
# ============================================

app.include_router(auth.router, prefix="/api/v1")
app.include_router(comprobantes.router, prefix="/api/v1")
app.include_router(veps.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(bank_kit.router, prefix="/api/v1")
app.include_router(alertas.router, prefix="/api/v1")
app.include_router(configuracion.router, prefix="/api/v1")
app.include_router(arco.router, prefix="/api/v1")
app.include_router(calendario.router, prefix="/api/v1")
app.include_router(ingesta.router, prefix="/api/v1")

# Webhooks externos (sin prefijo /api/v1 — vienen de Meta/WhatsApp)
app.include_router(whatsapp.router, prefix="/api/v1")


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
