"""
Contexto de request — variables globales por request.
Usado para pasar tenant_id al get_db() y activar RLS.
"""
from contextvars import ContextVar

current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)
