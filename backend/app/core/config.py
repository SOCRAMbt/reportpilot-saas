"""
Configuración del sistema usando Pydantic Settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, Literal
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Configuración principal de AccountantOS"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================
    # GENERAL
    # ============================================
    environment: Literal["development", "staging", "production"] = "development"
    secret_key: str = Field(..., min_length=32)
    frontend_url: str = "http://localhost:3000"

    # ============================================
    # BASE DE DATOS
    # ============================================
    database_url_override: Optional[str] = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "accountantos"
    database_user: str = "accountantos"
    database_password: str = Field(default="postgres", min_length=1)
    database_pool_size: int = 10
    database_max_overflow: int = 20

    @property
    def database_url(self) -> str:
        """URL de conexión a PostgreSQL o SQLite"""
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def async_database_url(self) -> str:
        """URL asíncrona para asyncpg o aiosqlite"""
        if self.database_url_override:
            if self.database_url_override.startswith("sqlite"):
                return self.database_url_override
            return self.database_url_override.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # ============================================
    # REDIS
    # ============================================
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """URL de conexión a Redis"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ============================================
    # ARCA/AFIP
    # ============================================
    arca_cert_path: str = Field(..., description="Ruta al certificado .cer")
    arca_key_path: str = Field(..., description="Ruta a la clave privada .key")
    arca_ca_path: str = Field(..., description="Ruta al CA de AFIP")
    arca_cuit_estudio: str = Field(..., min_length=11, max_length=11)
    arca_cert_password: Optional[str] = None
    arca_ambiente: Literal["hom", "pro"] = "hom"

    # URLs de WSAA según ambiente
    @property
    def arca_wsaa_url(self) -> str:
        """URL del WSAA según ambiente"""
        if self.arca_ambiente == "hom":
            return "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
        return "https://wsaa.afip.gov.ar/ws/services/LoginCms"

    # ============================================
    # GOOGLE CLOUD / GEMINI
    # ============================================
    google_cloud_project: Optional[str] = None
    google_cloud_key_path: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    gemini_location: str = "us-central1"

    # ============================================
    # SEGURIDAD - KMS
    # ============================================
    kms_provider: Literal["aws", "gcp", "vault"] = "gcp"
    kms_key_id: Optional[str] = None
    vault_url: Optional[str] = None
    vault_role_id: Optional[str] = None
    vault_secret_id: Optional[str] = None
    hmac_salt_master: str = Field(..., min_length=32)

    # ============================================
    # JWT
    # ============================================
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ============================================
    # CELERY
    # ============================================
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_worker_concurrency: int = 4

    # ============================================
    # RATE LIMITING
    # ============================================
    rate_limit_per_minute: int = 100
    rate_limit_redis_db: int = 2

    # ============================================
    # VEPs
    # ============================================
    vep_friction_threshold: float = 50000.0
    vep_pre_generacion_dias: int = 7

    # ============================================
    # SMTP / EMAIL
    # ============================================
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True

    # ============================================
    # WHATSAPP BUSINESS API
    # ============================================
    whatsapp_phone_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_webhook_secret: Optional[str] = None

    # ============================================
    # LOGGING
    # ============================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # ============================================
    # VALIDACIONES
    # ============================================
    @field_validator("arca_cuit_estudio")
    @classmethod
    def validate_cuit(cls, v: str) -> str:
        """Validar que el CUIT tenga 11 dígitos numéricos"""
        if not v.isdigit() or len(v) != 11:
            raise ValueError("CUIT debe tener 11 dígitos numéricos")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Obtener configuración cached (singleton)

    Returns:
        Settings: Configuración del sistema
    """
    return Settings()


# Instancia global para desarrollo
settings = get_settings()
