"""
Configuración de tests - Fixtures compartidos
"""

import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.core.config import settings

# ============================================
# CONFIGURACIÓN DE TEST
# ============================================

# Base de datos de test en memoria (SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    """Configurar backend para anyio (necesario para httpx async)"""
    return "asyncio"


@pytest.fixture(scope="function")
async def db_engine():
    """Crear engine de test"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Crear tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Crear sesión de test"""
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Crear cliente de test para FastAPI"""

    # Override de la dependencia get_db
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_cuit() -> str:
    """CUIT de ejemplo válido"""
    return "20123456789"


@pytest.fixture
def sample_comprobante_data() -> dict:
    """Datos de comprobante de ejemplo"""
    return {
        "tipo_comprobante": "A",
        "punto_venta": 1,
        "numero": 123456,
        "fecha_emision": "2026-03-28",
        "total": 1210.00,
        "neto_gravado": 1000.00,
        "iva": 210.00,
        "cuit_emisor": "20123456789",
        "cuit_receptor": "20987654321",
    }
