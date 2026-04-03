"""
Tests de autenticación
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.anyio
async def test_registro_usuario(client: AsyncClient, db_session: AsyncSession):
    """Test de registro de usuario"""
    response = await client.post(
        "/api/v1/auth/registro",
        json={
            "email": "test@estudio.com",
            "password": "password123",
            "nombre": "Test User",
            "tenant_id": 1,
            "rol": "operador",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@estudio.com"
    assert data["nombre"] == "Test User"
    assert "id" in data


@pytest.mark.anyio
async def test_login_usuario(client: AsyncClient, db_session: AsyncSession):
    """Test de login"""
    # Primero registrar usuario
    await client.post(
        "/api/v1/auth/registro",
        json={
            "email": "login@estudio.com",
            "password": "password123",
            "nombre": "Login Test",
            "tenant_id": 1,
        },
    )

    # Intentar login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@estudio.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_password_incorrecta(client: AsyncClient):
    """Test de login con contraseña incorrecta"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "noexiste@estudio.com",
            "password": "passwordincorrecto",
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_cuit_validacion():
    """Test de validación de CUIT"""
    from app.core.security import tokenizar_cuit, verificar_token_cuit

    cuit = "20123456789"
    tenant_id = 1

    token = tokenizar_cuit(cuit, tenant_id)

    assert len(token) == 20
    assert token.isupper()
    assert verificar_token_cuit(token, cuit, tenant_id)
    assert not verificar_token_cuit(token, "20987654321", tenant_id)
