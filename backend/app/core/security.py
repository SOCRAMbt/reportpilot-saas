"""
Módulo de seguridad - HMAC, hashing, JWT y gestión de contraseñas
"""

import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

# ============================================
# CONFIGURACIÓN
# ============================================

# Contexto para hashing de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================
# HMAC-SHA256 CON SALT (Para tokenización de CUITs)
# ============================================


def get_hmac_key(tenant_id: int) -> bytes:
    """
    Obtener clave HMAC derivada del salt maestro y tenant_id

    Args:
        tenant_id: ID del tenant/estudio

    Returns:
        bytes: Clave HMAC derivada
    """
    # En producción, esto viene del KMS
    salt_master = settings.hmac_salt_master.encode("utf-8")
    tenant_bytes = str(tenant_id).encode("utf-8")

    # Derivar clave: HMAC-SHA256(salt_master, tenant_id)
    derived_key = hmac.new(salt_master, tenant_bytes, hashlib.sha256).digest()
    return derived_key


def tokenizar_cuit(cuit: str, tenant_id: int) -> str:
    """
    Tokenizar un CUIT usando HMAC-SHA256 con salt por tenant

    El mismo CUIT genera tokens diferentes para distintos tenants.
    El token es truncado a 20 caracteres hex (80 bits de seguridad).

    Args:
        cuit: CUIT a tokenizar (11 dígitos)
        tenant_id: ID del tenant

    Returns:
        str: Token hexadecimal (20 caracteres)
    """
    if len(cuit) != 11 or not cuit.isdigit():
        raise ValueError("CUIT debe tener 11 dígitos numéricos")

    key = get_hmac_key(tenant_id)
    token = hmac.new(key, cuit.encode("utf-8"), hashlib.sha256).hexdigest()
    return token[:20].upper()  # 20 hex chars = 80 bits


def verificar_token_cuit(token: str, cuit: str, tenant_id: int) -> bool:
    """
    Verificar si un token corresponde a un CUIT dado

    Args:
        token: Token a verificar
        cuit: CUIT original
        tenant_id: ID del tenant

    Returns:
        bool: True si el token es válido
    """
    expected_token = tokenizar_cuit(cuit, tenant_id)
    return hmac.compare_digest(token, expected_token)


# ============================================
# HASHING DE CONTRASEÑAS
# ============================================


def hash_password(password: str) -> str:
    """
    Hashear una contraseña usando bcrypt

    Args:
        password: Contraseña en texto plano

    Returns:
        str: Contraseña hasheada
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar una contraseña contra su hash

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash bcrypt

    Returns:
        bool: True si la contraseña es correcta
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================
# JWT (JSON Web Tokens)
# ============================================


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear un JWT de acceso

    Args:
        data: Datos a incluir en el token (ej: {"sub": user_id, "tenant_id": 1})
        expires_delta: Tiempo de expiración (default: 30 minutos)

    Returns:
        str: JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear un JWT de refresco (larga duración)

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración (default: 7 días)

    Returns:
        str: JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decodificar y validar un JWT

    Args:
        token: JWT a decodificar

    Returns:
        dict | None: Datos del token o None si es inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Verificar un token de acceso (no debe ser tipo 'refresh')

    Args:
        token: JWT a verificar

    Returns:
        dict | None: Datos del token o None si es inválido/expirado
    """
    payload = decode_token(token)

    if payload is None:
        return None

    if payload.get("type") == "refresh":
        return None

    return payload
