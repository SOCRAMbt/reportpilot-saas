"""
Schemas de autenticación
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UsuarioBase(BaseModel):
    """Schema base para usuario"""
    email: EmailStr
    nombre: str


class UsuarioCreate(UsuarioBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8)
    tenant_id: int
    rol: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    """Schema para respuesta de usuario"""
    id: int
    rol: str
    tenant_id: int

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema para respuesta de login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class TokenRefreshRequest(BaseModel):
    """Schema para refresh de token"""
    refresh_token: str
