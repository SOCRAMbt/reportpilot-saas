"""
Router de configuraci\u00f3n de certificados ARCA

Permite a los contadores subir y gestionar certificados y claves privadas
sin tocar el archivo .env.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import os
import logging
from datetime import date

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

from app.db import get_db
from app.models import Tenant
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/configuracion", tags=["Configuraci\u00f3n"])

# Directorio seguro para certificados (fuera de /tmp)
CERTS_DIR = Path("/app/certs")

# Extensiones v\u00e1lidas
CERT_EXTENSIONS = {".cer", ".pem", ".crt"}
KEY_EXTENSIONS = {".key", ".pem"}


def _get_cert_dir(tenant_id: int) -> Path:
    """Obtiene el directorio de certificados del tenant."""
    return CERTS_DIR / f"tenant_{tenant_id}"


def _validate_pem_certificate(content: bytes) -> bool:
    """Valida que el contenido sea un certificado PEM v\u00e1lido."""
    try:
        load_pem_x509_certificate(content, default_backend())
        return True
    except Exception:
        return False


def _validate_pem_private_key(content: bytes) -> bool:
    """Valida que el contenido sea una clave privada PEM v\u00e1lida."""
    try:
        load_pem_private_key(content, password=None, backend=default_backend())
        return True
    except Exception:
        return False


@router.get("/arca/estado")
async def obtener_estado_arca(
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Verifica el estado de los certificados ARCA configurados.

    Revisa si existen los archivos de certificado y clave privada,
    y valida su integridad criptogr\u00e1fica.
    """
    # Verificar que el tenant existe
    resultado = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = resultado.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    cert_dir = _get_cert_dir(tenant_id)
    cert_path = cert_dir / "certificado.cer"
    key_path = cert_dir / "clave_privada.key"

    cert_ok = cert_path.exists()
    key_ok = key_path.exists()

    cert_valido = False
    cert_info = {"presente": cert_ok, "valido": False, "subject": None, "valid_from": None, "valid_until": None, "vencido": False}
    key_valido = False

    # Validar certificado
    if cert_ok:
        try:
            content = cert_path.read_bytes()
            cert = load_pem_x509_certificate(content, default_backend())
            cert_valido = True
            cert_info["valido"] = True
            cert_info["subject"] = cert.subject.rfc4514_string()
            cert_info["valid_from"] = cert.not_valid_before_utc.isoformat()
            cert_info["valid_until"] = cert.not_valid_after_utc.isoformat()
            cert_info["vencido"] = cert.not_valid_after_utc.date() < date.today()
        except Exception as e:
            logger.warning("Certificado presente pero no v\u00e1lido", tenant_id=tenant_id, error=str(e))
            cert_info["valido"] = False

    # Validar clave privada
    if key_ok:
        try:
            content = key_path.read_bytes()
            load_pem_private_key(content, password=None, backend=default_backend())
            key_valido = True
        except Exception as e:
            logger.warning("Clave privada presente pero no v\u00e1lida", tenant_id=tenant_id, error=str(e))

    listo_para_produccion = cert_valido and key_valido

    instrucciones = None
    if not listo_para_produccion:
        instrucciones = (
            "Para comenzar: 1) Descarga tu certificado de ARCA. "
            "2) Sube el archivo .cer. "
            "3) Sube la clave privada .key."
        )

    return {
        "listo_para_produccion": listo_para_produccion,
        "certificado": cert_info,
        "clave_privada": {"presente": key_ok, "valido": key_valido},
        "instrucciones": instrucciones,
    }


@router.post("/arca/certificado", status_code=status.HTTP_201_CREATED)
async def subir_certificado(
    archivo: UploadFile = File(description="Archivo .cer o .pem de ARCA"),
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Sube el certificado p\u00fablico de ARCA (.cer, .pem, .crt).

    El archivo se valida criptogr\u00e1ficamente antes de guardarse.
    """
    # Verificar que el tenant existe
    resultado = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = resultado.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    # Validar extensi\u00f3n del archivo
    if archivo.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no tiene nombre",
        )

    suffix = Path(archivo.filename).suffix.lower()
    if suffix not in CERT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensi\u00f3n no v\u00e1lida. Use una de: {', '.join(sorted(CERT_EXTENSIONS))}",
        )

    # Leer contenido
    content = await archivo.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo est\u00e1 vac\u00edo",
        )

    # Validar que es un certificado real
    if not _validate_pem_certificate(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no contiene un certificado PEM v\u00e1lido",
        )

    # Parsear para extraer informaci\u00f3n
    cert = load_pem_x509_certificate(content, default_backend())
    valid_until = cert.not_valid_after_utc.date()
    dias_para_vencimiento = (valid_until - date.today()).days

    # Guardar archivo
    cert_dir = _get_cert_dir(tenant_id)
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "certificado.cer"
    cert_path.write_bytes(content)
    os.chmod(str(cert_path), 0o600)

    alerta = None
    if dias_para_vencimiento < 60:
        alerta = f"El certificado vence en {dias_para_vencimiento} d\u00edas. Considere renovarlo pronto."

    return {
        "mensaje": "Certificado cargado correctamente",
        "subject": cert.subject.rfc4514_string(),
        "valido_hasta": valid_until.isoformat(),
        "dias_para_vencimiento": dias_para_vencimiento,
        "alerta": alerta,
    }


@router.post("/arca/clave-privada", status_code=status.HTTP_201_CREATED)
async def subir_clave_privada(
    archivo: UploadFile = File(description="Archivo .key o .pem de clave privada"),
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Sube la clave privada asociada al certificado ARCA (.key, .pem).

    Se valida criptogr\u00e1ficamente antes de guardarse.
    """
    # Verificar que el tenant existe
    resultado = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = resultado.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    # Validar extensi\u00f3n del archivo
    if archivo.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no tiene nombre",
        )

    suffix = Path(archivo.filename).suffix.lower()
    if suffix not in KEY_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensi\u00f3n no v\u00e1lida. Use una de: {', '.join(sorted(KEY_EXTENSIONS))}",
        )

    # Leer contenido
    content = await archivo.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo est\u00e1 vac\u00edo",
        )

    # Validar que es una clave privada real
    if not _validate_pem_private_key(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no contiene una clave privada PEM v\u00e1lida (sin contrase\u00f1a)",
        )

    # Guardar archivo
    cert_dir = _get_cert_dir(tenant_id)
    cert_dir.mkdir(parents=True, exist_ok=True)
    key_path = cert_dir / "clave_privada.key"
    key_path.write_bytes(content)
    os.chmod(str(key_path), 0o600)

    return {"mensaje": "Clave privada cargada correctamente"}


@router.post("/arca/configurar-estudio")
async def configurar_estudio(
    body: dict,
    tenant_id: int = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Configura el CUIT del estudio y el ambiente ARCA (homologaci\u00f3n / producci\u00f3n).

    - **cuit_estudio**: CUIT de 11 d\u00edgitos (se aceptan guiones y espacios)
    - **nombre_estudio**: Nombre del estudio contable
    - **ambiente**: "hom" para homologaci\u00f3n, "pro" para producci\u00f3n
    """
    # Verificar que el tenant existe
    resultado = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = resultado.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    # Extraer y validar campos
    cuit_estudio = body.get("cuit_estudio", "").strip().replace("-", "").replace(" ", "")
    nombre_estudio = body.get("nombre_estudio", "").strip()
    ambiente = body.get("ambiente", "hom").strip().lower()

    if not cuit_estudio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El campo 'cuit_estudio' es obligatorio",
        )

    if not cuit_estudio.isdigit() or len(cuit_estudio) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El CUIT debe tener exactamente 11 d\u00edgitos num\u00e9ricos",
        )

    if not nombre_estudio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El campo 'nombre_estudio' es obligatorio",
        )

    if ambiente not in ("hom", "pro"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El campo 'ambiente' debe ser 'hom' o 'pro'",
        )

    # Construir rutas de certificados
    cert_dir = _get_cert_dir(tenant_id)
    cert_path = str(cert_dir / "certificado.cer")
    key_path = str(cert_dir / "clave_privada.key")

    # Actualizar configuraci\u00f3n del tenant
    configuracion = tenant.configuracion or {}
    configuracion["arca_cuit_estudio"] = cuit_estudio
    configuracion["arca_ambiente"] = ambiente
    configuracion["nombre_estudio"] = nombre_estudio
    configuracion["arca_cert_path"] = cert_path
    configuracion["arca_key_path"] = key_path
    tenant.configuracion = configuracion

    session.add(tenant)
    await session.commit()

    ambiente_label = "producci\u00f3n" if ambiente == "pro" else "homologaci\u00f3n"

    return {
        "mensaje": f"Estudio configurado correctamente en ambiente de {ambiente_label}",
        "cuit_estudio": cuit_estudio,
        "nombre_estudio": nombre_estudio,
        "ambiente": ambiente,
        "proximo_paso": "Sube tu certificado .cer y clave .key en /configuracion/arca/certificado y /configuracion/arca/clave-privada",
    }
