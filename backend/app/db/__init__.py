"""
Módulo de base de datos - Conexiones y sesiones
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy import create_engine
from app.core.config import settings

# ============================================
# DETECTAR SI USAMOS SQLITE
# ============================================

is_sqlite = settings.async_database_url.startswith("sqlite")

# ============================================
# BASE DE DATOS SÍNCRONA (para Alembic migrations)
# ============================================

if is_sqlite:
    sync_engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
else:
    sync_engine = create_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)

# ============================================
# BASE DE DATOS ASÍNCRONA (para FastAPI)
# ============================================

if is_sqlite:
    async_engine = create_async_engine(
        settings.async_database_url,
        connect_args={"check_same_thread": False},
    )
else:
    async_engine = create_async_engine(
        settings.async_database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ============================================
# BASE DECLARATIVA
# ============================================

Base = declarative_base()


# ============================================
# DEPENDENCIAS PARA FASTAPI
# ============================================

async def get_db() -> AsyncSession:
    """
    Dependencia para obtener sesión de BD en FastAPI.
    Activa RLS ejecutando set_config('app.current_tenant', ...)
    antes de cualquier query.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Activar Row-Level Security para este tenant
            from app.core.context import current_tenant_id
            from sqlalchemy import text

            tenant_id = current_tenant_id.get()
            if tenant_id and not is_sqlite:
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :tid, true)"),
                    {"tid": str(tenant_id)}
                )

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    Dependencia para obtener sesión síncrona (Alembic, scripts)

    Yields:
        Session: Sesión de base de datos síncrona
    """
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
