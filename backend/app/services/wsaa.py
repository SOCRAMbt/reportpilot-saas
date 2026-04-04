"""
Servicio WSAA - Autenticación con ARCA/AFIP

Genera y gestiona tokens de autenticación para los web services de ARCA.
Implementa:
- Generación de TRA (Ticket de Request de Acceso)
- Obtención de TA (Ticket de Acceso) desde WSAA
- Caché de tokens en Redis (sin persistencia)
- Sync NTP con time.afip.gov.ar
"""

import hashlib
import logging
import secrets
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import redis
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs7, Encoding
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate

from app.core.config import settings
from app.models import WSAAToken
from app.db import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTES
# ============================================

# TTL de tokens (en segundos)
# Los tokens WSAA duran 2 horas, usamos TTL preventivo
TOKEN_TTL_PRODUCCION = 7080  # 7200 - 120 de margen (correcto)
TOKEN_TTL_TESTING = 600  # 10 minutos para testing

# Servicios disponibles
SERVICIOS = {
    "wsfe": "wsfe",
    "wsfex": "wsfex",
    "wscdc": "wscdc",
    "wsbfe": "wsbfe",
    "wsct": "wsct",
    "wsmtxca": "wsmtxca",
    "padron_a4": "padron-a4",
    "padron_a5": "padron-a5",
    "constancia_inscripcion": "constancia-inscripcion",
}


# ============================================
# UTILIDADES NTP
# ============================================

def sync_ntp_afip() -> Optional[datetime]:
    """
    Sincronizar reloj con time.afip.gov.ar

    Los tokens WSAA son sensibles al desfase horario.
    Error común: 'El CEE ya posee un TA válido' por clock skew.

    Returns:
        datetime | None: Hora actual según AFIP o None si falla
    """
    import socket
    import struct
    import time

    try:
        # Implementación SNTP simple (RFC 5905)
        host = "time.afip.gov.ar"
        port = 123
        timeout = 5

        # Crear packet SNTP (modo 3 = cliente, versión 4)
        ntp_packet = bytes([0x1B] + [0] * 47)

        # Conectar y enviar packet
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout)
            client.sendto(ntp_packet, (host, port))

            # Recibir respuesta
            response, _ = client.recvfrom(1024)

            # Extraer timestamp del servidor (segundos desde 1900)
            if len(response) >= 48:
                server_time = struct.unpack("!12I", response)[10]

                # Convertir a epoch Unix (restar 70 años en segundos)
                unix_time = server_time - 2208988800

                # Calcular offset del reloj local
                local_time = time.time()
                offset = unix_time - local_time

                # Loguear offset para diagnóstico
                if abs(offset) > 1.0:
                    logger.warning(f"Clock skew detectado: {offset:+.2f} segundos")
                else:
                    logger.debug("Reloj sincronizado con time.afip.gov.ar (offset < 1s)")

                # Devolver hora sincronizada (sin ajustar reloj del sistema - requiere root)
                # El caller debe usar esta hora para generar timestamps
                logger.info("NTP sync exitoso con time.afip.gov.ar")
                return datetime.now() + timedelta(seconds=offset)

    except (socket.timeout, socket.error, struct.error) as e:
        logger.warning(f"NTP sync falló con time.afip.gov.ar: {e}")

    except Exception as e:
        logger.warning(f"NTP sync falló: {e}")

    # Fallback: usar hora local
    logger.warning("Usando hora local como fallback")
    return datetime.now()


def get_afip_time() -> datetime:
    """
    Obtener hora actual (GMT-3 para AFIP)

    Returns:
        datetime: Hora actual en zona horaria AFIP
    """
    # AFIP usa Argentina Time (GMT-3)
    # Sincronizar con servidor NTP de AFIP para evitar clock skew
    afip_time = sync_ntp_afip()
    return afip_time or datetime.now()


# ============================================
# GENERACIÓN DE TRA (Ticket de Request de Acceso)
# ============================================

def generar_tra(servicio: str) -> str:
    """
    Generar Ticket de Request de Acceso (TRA)

    El TRA es un XML firmado que solicita un token para un servicio.

    Args:
        servicio: Nombre del servicio (wsfe, wsfex, etc.)

    Returns:
        str: TRA firmado en base64
    """
    if servicio not in SERVICIOS:
        raise ValueError(f"Servicio {servicio} no válido")

    # Timestamps
    now = get_afip_time()
    fecha = now.strftime("%Y-%m-%dT%H:%M:%S-03:00")

    # Generar número de transacción único (hash de timestamp + random)
    transaccion = hashlib.sha256(
        f"{now.timestamp()}{secrets.token_hex(8)}".encode()
    ).hexdigest()[:10]

    # Construir XML del TRA
    tra_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{transaccion}</uniqueId>
        <generationTime>{fecha}</generationTime>
        <expirationTime>{(now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S-03:00")}</expirationTime>
    </header>
    <service>{SERVICIOS[servicio]}</service>
</loginTicketRequest>
"""

    # Firmar el TRA con PKCS7/CMS (estándar ARCA)
    tra_firmado = firmar_tra(tra_xml)

    logger.debug(f"TRA generado para servicio {servicio}")
    return tra_firmado


def firmar_tra(tra_xml: str) -> str:
    """
    Firmar digitalmente el TRA usando CMS/PKCS7 (estándar ARCA/AFIP WSAA)

    El WSAA de ARCA requiere que el request sea el TRA XML + la firma CMS
    como campos separados del POST. Sin embargo, para compatibilidad con
    el flujo existente, devolvemos el TRA firmado con la firma PKCS7
    embebida en base64.

    Args:
        tra_xml: XML del TRA sin firmar

    Returns:
        str: TRA firmado en base64 (CMS PKCS7)
    """
    # Cargar certificado y clave
    cert_path = Path(settings.arca_cert_path)
    key_path = Path(settings.arca_key_path)

    if not cert_path.exists() or not key_path.exists():
        raise FileNotFoundError(
            f"Certificado o clave no encontrados. Verificar rutas:\n"
            f"  Certificado: {settings.arca_cert_path}\n"
            f"  Clave: {settings.arca_key_path}"
        )

    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=settings.arca_cert_password.encode() if settings.arca_cert_password else None,
            backend=default_backend()
        )

    with open(cert_path, "rb") as f:
        certificate = load_pem_x509_certificate(f.read(), backend=default_backend())

    # Firmar con CMS/PKCS7 — estándar ARCA/AFIP
    tra_bytes = tra_xml.encode("utf-8")

    signed = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra_bytes)
        .add_signer(certificate, private_key, hashes.SHA256())
        .sign(Encoding.PEM, [pkcs7.PKCS7Options.DetachedSignature])
    )

    # ARCA WSAA requiere: request=TRA_xml_b64 & cms=firmapem
    # Codificamos ambos para poder separarlos en obtener_ta()
    tra_b64 = base64.b64encode(tra_bytes).decode("utf-8")
    cms_b64 = base64.b64encode(signed).decode("utf-8")

    # Formato: TRA.b64|CMS.b64 (separados por | para poder parsear)
    return f"{tra_b64}|{cms_b64}"


async def firmar_tra_para_tenant(tra_xml: str, tenant_id: int) -> str:
    """
    Firmar TRA usando el certificado del tenant específico.
    El certificado se subió desde la UI de Configuración → ARCA.

    Args:
        tra_xml: XML del TRA sin firmar
        tenant_id: ID del tenant

    Returns:
        str: TRA firmado en formato TRA.b64|CMS.b64
    """
    # Directorio del certificado del tenant
    tenant_cert_dir = Path("/app/certs") / f"tenant_{tenant_id}"
    cert_path = tenant_cert_dir / "certificado.cer"
    key_path = tenant_cert_dir / "clave_privada.key"

    if not cert_path.exists():
        raise FileNotFoundError(
            f"Certificado no encontrado para tenant {tenant_id}. "
            "El contador debe subir su certificado en Configuración → ARCA."
        )

    if not key_path.exists():
        raise FileNotFoundError(
            f"Clave privada no encontrada para tenant {tenant_id}. "
            "El contador debe subir su clave privada en Configuración → ARCA."
        )

    # Cargar certificado y clave
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=settings.arca_cert_password.encode() if settings.arca_cert_password else None,
            backend=default_backend()
        )

    with open(cert_path, "rb") as f:
        certificate = load_pem_x509_certificate(f.read(), backend=default_backend())

    # Firmar con CMS/PKCS7
    tra_bytes = tra_xml.encode("utf-8")

    signed = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra_bytes)
        .add_signer(certificate, private_key, hashes.SHA256())
        .sign(Encoding.PEM, [pkcs7.PKCS7Options.DetachedSignature])
    )

    tra_b64 = base64.b64encode(tra_bytes).decode("utf-8")
    cms_b64 = base64.b64encode(signed).decode("utf-8")

    return f"{tra_b64}|{cms_b64}"


# ============================================
# SOLICITUD DE TA (Ticket de Acceso)
# ============================================

async def obtener_ta(servicio: str) -> tuple[str, str]:
    """
    Obtener Ticket de Acceso (TA) desde WSAA

    El TA contiene token y signature válidos por 2 horas.

    Args:
        servicio: Nombre del servicio

    Returns:
        tuple[str, str]: (token, signature)
    """
    import httpx

    # Generar TRA firmado (formato: TRA.b64|CMS.b64)
    tra_firmado = generar_tra(servicio)

    # Separar TRA y CMS
    tra_b64, cms_b64 = tra_firmado.split("|", 1)

    # Enviar solicitud a WSAA
    # ARCA WSAA requiere dos campos: 'request' (TRA b64) y 'cms' (firma b64)
    async with httpx.AsyncClient(
        timeout=30.0,
        verify=settings.arca_ca_path
    ) as client:
        try:
            response = await client.post(
                settings.arca_wsaa_url,
                data={
                    "request": tra_b64,
                    "cms": cms_b64,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

        except httpx.HTTPError as e:
            logger.error(f"Error al obtener TA: {e}")
            raise

    # Parsear respuesta XML
    ta_xml = response.text
    token, signature = parsear_ta(ta_xml)

    logger.info(f"TA obtenido para servicio {servicio}")
    return token, signature


def parsear_ta(ta_xml: str) -> tuple[str, str]:
    """
    Parsear XML del TA y extraer token y signature

    Args:
        ta_xml: XML del Ticket de Acceso

    Returns:
        tuple[str, str]: (token, signature)
    """
    try:
        root = ET.fromstring(ta_xml)

        # Manejar namespaces
        ns = {"": "http://wsaa.afip.gov.ar/ws/services/LoginCms"}

        # Extraer token y signature
        token_elem = root.find(".//token", ns)
        signature_elem = root.find(".//signature", ns)

        if token_elem is None or signature_elem is None:
            # Intentar sin namespace
            token_elem = root.find(".//token")
            signature_elem = root.find(".//signature")

        if token_elem is None or signature_elem is None:
            raise ValueError(f"No se pudo parsear TA: {ta_xml[:200]}")

        return token_elem.text, signature_elem.text

    except ET.ParseError as e:
        logger.error(f"Error al parsear TA: {e}")
        raise


# ============================================
# GESTIÓN DE TOKENS (Caché Redis)
# ============================================

async def get_token_para_servicio(
    session,
    tenant_id: int,
    servicio: str,
    force_refresh: bool = False
) -> tuple[str, str]:
    """
    Obtener token para un servicio (con caché Redis)

    1. Verifica si hay token válido en caché
    2. Si no hay o está por vencer, solicita nuevo TA
    3. Guarda en caché

    Args:
        session: Sesión de base de datos
        tenant_id: ID del tenant
        servicio: Nombre del servicio
        force_refresh: Forzar renovación del token

    Returns:
        tuple[str, str]: (token, signature)
    """
    redis_client = redis.from_url(settings.redis_url)

    try:
        # Clave de caché
        cache_key = f"wsaa:token:{tenant_id}:{servicio}"

        # Intentar obtener de caché
        if not force_refresh:
            cached = redis_client.hgetall(cache_key)
            if cached:
                t = cached.get(b"token") or cached.get("token")
                s = cached.get(b"signature") or cached.get("signature")
                if t and s:
                    logger.debug(f"Token en caché para {servicio}")
                    return (t.decode() if isinstance(t, bytes) else t,
                            s.decode() if isinstance(s, bytes) else s)

        # Solicitar nuevo token
        token, signature = await obtener_ta(servicio)

        # Calcular TTL (2 horas menos margen de seguridad)
        ttl = TOKEN_TTL_PRODUCCION if settings.environment == "production" else TOKEN_TTL_TESTING

        # Guardar en caché (sin persistencia - Redis está configurado sin AOF/RDB)
        redis_client.hset(cache_key, mapping={
            "token": token,
            "signature": signature,
            "expires_in": ttl
        })
        redis_client.expire(cache_key, ttl)

        # Guardar en BD también (para auditoría)
        await guardar_token_en_bd(session, tenant_id, servicio, token, signature)

        logger.info(f"Token renovado para {servicio} (TTL: {ttl}s)")
        return token, signature
    finally:
        redis_client.close()


async def guardar_token_en_bd(
    session,
    tenant_id: int,
    servicio: str,
    token: str,
    signature: str
):
    """
    Guardar token en base de datos (auditoría)

    Args:
        session: Sesión de BD
        tenant_id: ID del tenant
        servicio: Nombre del servicio
        token: Token WSAA
        signature: Signature WSAA
    """
    from sqlalchemy import delete

    # Eliminar token anterior
    await session.execute(
        delete(WSAAToken).where(
            WSAAToken.tenant_id == tenant_id,
            WSAAToken.servicio == servicio
        )
    )

    # Crear nuevo token
    nuevo_token = WSAAToken(
        tenant_id=tenant_id,
        servicio=servicio,
        token=token,
        signature=signature,
        vencimiento=datetime.now() + timedelta(hours=2)
    )

    session.add(nuevo_token)
    await session.commit()

    logger.debug(f"Token guardado en BD para tenant {tenant_id}, servicio {servicio}")


# ============================================
# INVALIDACIÓN DE TOKENS
# ============================================

async def invalidar_token(tenant_id: int, servicio: str):
    """
    Invalidar token en caché (para forzar renovación)

    Args:
        tenant_id: ID del tenant
        servicio: Nombre del servicio
    """
    redis_client = redis.from_url(settings.redis_url)
    try:
        cache_key = f"wsaa:token:{tenant_id}:{servicio}"
        redis_client.delete(cache_key)
        logger.info(f"Token invalidado para {servicio}")
    finally:
        redis_client.close()


# ============================================
# HEALTH CHECK
# ============================================

async def verificar_conexion_wsaa() -> bool:
    """
    Verificar conexión con WSAA

    Returns:
        bool: True si WSAA está accesible
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.arca_wsaa_url.replace("/LoginCms", ""))
            return response.status_code == 200
    except Exception:
        return False
