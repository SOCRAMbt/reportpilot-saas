"""
Endpoints de autenticación y gestión de usuarios
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import Usuario, Tenant
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    UsuarioCreate,
    UsuarioResponse,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])
security = HTTPBearer()


@router.post("/registro", response_model=UsuarioResponse)
async def registro(
    data: UsuarioCreate,
    session: AsyncSession = Depends(get_db)
):
    """
    Registrar nuevo usuario en un tenant existente

    Requiere email único dentro del tenant.
    """
    # Verificar que el tenant existe
    resultado = await session.execute(
        select(Tenant).where(Tenant.id == data.tenant_id)
    )
    tenant = resultado.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado"
        )

    # Verificar email no duplicado
    resultado = await session.execute(
        select(Usuario).where(
            Usuario.email == data.email,
            Usuario.tenant_id == data.tenant_id
        )
    )

    if resultado.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ya registrado en este tenant"
        )

    # Crear usuario
    usuario = Usuario(
        tenant_id=data.tenant_id,
        email=data.email,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        rol=data.rol or "operador"
    )

    session.add(usuario)
    await session.commit()
    await session.refresh(usuario)

    return UsuarioResponse(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        rol=usuario.rol,
        tenant_id=usuario.tenant_id
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Iniciar sesión y obtener tokens JWT

    Devuelve access_token (30 min) y refresh_token (7 días)
    """
    # Buscar usuario por email
    resultado = await session.execute(
        select(Usuario).where(
            Usuario.email == data.email,
            Usuario.activo == True
        )
    )
    usuario = resultado.scalar_one_or_none()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Verificar contraseña
    if not verify_password(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Generar tokens
    access_token = create_access_token(
        data={
            "sub": str(usuario.id),
            "tenant_id": usuario.tenant_id,
            "email": usuario.email,
            "rol": usuario.rol
        }
    )

    refresh_token = create_refresh_token(
        data={
            "sub": str(usuario.id),
            "tenant_id": usuario.tenant_id
        }
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        usuario=UsuarioResponse(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            rol=usuario.rol,
            tenant_id=usuario.tenant_id
        )
    )


@router.post("/refresh")
async def refresh_token(
    data: TokenRefreshRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Renovar access_token usando refresh_token
    """
    payload = verify_access_token(data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )

    # Verificar que el usuario existe y está activo
    resultado = await session.execute(
        select(Usuario).where(
            Usuario.id == int(payload.get("sub")),
            Usuario.activo == True
        )
    )
    usuario = resultado.scalar_one_or_none()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )

    # Generar nuevo access_token
    access_token = create_access_token(
        data={
            "sub": str(usuario.id),
            "tenant_id": usuario.tenant_id,
            "email": usuario.email,
            "rol": usuario.rol
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UsuarioResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db)
):
    """
    Obtener datos del usuario autenticado
    """
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

    resultado = await session.execute(
        select(Usuario).where(Usuario.id == int(payload.get("sub")))
    )
    usuario = resultado.scalar_one_or_none()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return UsuarioResponse(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        rol=usuario.rol,
        tenant_id=usuario.tenant_id
    )


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Dependencia para obtener ID del usuario autenticado
    """
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

    return int(payload.get("sub"))


def get_current_tenant_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Dependencia para obtener tenant_id del usuario autenticado
    """
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

    return int(payload.get("tenant_id"))
