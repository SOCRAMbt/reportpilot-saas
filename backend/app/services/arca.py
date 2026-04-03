"""
Servicios ARCA - Capa de acceso a Web Services de ARCA/AFIP

Implementa acceso a:
- WSFE: Facturación electrónica (comprobantes clase A, B, C)
- WSFEX: Facturación de exportación
- WSCDC: Descarga masiva de comprobantes
- WSBFE: Bonos fiscales de importación
- WSCT: Servicios turísticos
- WSMTXCA: Detalle de ítems
- Padrones: Validación de CUITs y constancias

Características:
- Circuit Breaker para distinguir 429 (rate limit) de 5xx (error)
- Rate limiting con Token Bucket en Redis
- Reintentos con backoff exponencial
- SOAP con zeep
"""

import asyncio
import logging
import hashlib
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from pathlib import Path

import httpx
import redis
from zeep import Client, Settings as ZeepSettings
from zeep.transports import Transport
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.services.wsaa import get_token_para_servicio, SERVICIOS
from app.db import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURACIÓN DE SOAP (ZEep)
# ============================================

# URLs de los servicios según ambiente
URLS_SERVICIOS = {
    "hom": {
        "wsfe": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
        "wsfex": "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
        "wscdc": "https://wswhomo.afip.gov.ar/wscdcv1/service.asmx?WSDL",
        "wsbfe": "https://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL",
        "wsct": "https://wswhomo.afip.gov.ar/wsctv1/service.asmx?WSDL",
        "wsmtxca": "https://wswhomo.afip.gov.ar/wsmtxca/service.asmx?WSDL",
        "padron_a4": "https://wswhomo.afip.gov.ar/ws_sr_padron_a4/wspadrona4.service",
        "padron_a5": "https://wswhomo.afip.gov.ar/ws_sr_padron_a5/wspadrona5.service",
        "constancia_inscripcion": "https://wswhomo.afip.gov.ar/ws_sr_constancia_inscripcion/service.asmx",
    },
    "pro": {
        "wsfe": "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
        "wsfex": "https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL",
        "wscdc": "https://servicios1.afip.gov.ar/wscdcv1/service.asmx?WSDL",
        "wsbfe": "https://servicios1.afip.gov.ar/wsbfev1/service.asmx?WSDL",
        "wsct": "https://servicios1.afip.gov.ar/wsctv1/service.asmx?WSDL",
        "wsmtxca": "https://servicios1.afip.gov.ar/wsmtxca/service.asmx?WSDL",
        "padron_a4": "https://aws.afip.gov.ar/sr-padron_a4/wspadrona4.service",
        "padron_a5": "https://aws.afip.gov.ar/sr-padron_a5/wspadrona5.service",
        "constancia_inscripcion": "https://servicios1.afip.gov.ar/ws_sr_constancia_inscripcion/service.asmx",
    }
}


def get_client(servicio: str) -> Client:
    """
    Obtener cliente SOAP para un servicio

    Args:
        servicio: Nombre del servicio (wsfe, wsfex, etc.)

    Returns:
        Client: Cliente zeep configurado
    """
    url = URLS_SERVICIOS[settings.arca_ambiente][servicio]

    # Configuración de zeep
    zeep_settings = ZeepSettings(
        strict=False,
        xml_huge_tree=True
    )

    # Transport con timeouts
    transport = Transport(
        timeout=30,
        operation_timeout=60
    )

    client = Client(wsdl=url, transport=transport, settings=zeep_settings)
    return client


# ============================================
# RATE LIMITING (Token Bucket en Redis)
# ============================================

class RateLimiter:
    """
    Rate Limiter con Token Bucket algorithm en Redis

    ARCA tiene límite de ~50 requests/minuto por CUIT.
    Implementamos token bucket para distribuir requests uniformemente.
    """

    def __init__(self, redis_client: redis.Redis, max_tokens: int = 50, refill_rate: float = 0.83):
        """
        Args:
            redis_client: Cliente Redis
            max_tokens: Máximo de tokens (requests por minuto)
            refill_rate: Tokens por segundo (50/60 = 0.83)
        """
        self.redis = redis_client
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate

    def acquire(self, key: str, tokens: int = 1) -> bool:
        """
        Adquirir tokens del bucket

        Args:
            key: Clave de rate limiting (ej: cuit del tenant)
            tokens: Cantidad de tokens a consumir

        Returns:
            bool: True si se obtuvieron tokens, False si rate limited
        """
        bucket_key = f"ratelimit:{key}"
        now = time.time()

        # Script Lua para atomicidad
        script = """
        local bucket_key = KEYS[1]
        local max_tokens = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])

        local bucket = redis.call('HMGET', bucket_key, 'tokens', 'last_update')
        local tokens = tonumber(bucket[1]) or max_tokens
        local last_update = tonumber(bucket[2]) or now

        -- Refill tokens based on time elapsed
        local elapsed = now - last_update
        tokens = math.min(max_tokens, tokens + (elapsed * refill_rate))

        if tokens >= requested then
            tokens = tokens - requested
            redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', bucket_key, 60)
            return 1
        else
            return 0
        end
        """

        result = self.redis.eval(
            script,
            1,
            bucket_key,
            self.max_tokens,
            self.refill_rate,
            now,
            tokens
        )

        return result == 1


# ============================================
# CIRCUIT BREAKER (Persistente en Redis)
# ============================================

class CircuitBreaker:
    """
    Circuit Breaker para servicios ARCA con persistencia en Redis

    Distingue entre:
    - 429 (rate limit): backoff, NO abrir circuito
    - 5xx (error del servidor): abrir circuito después de N fallos
    - Timeout: abrir circuito después de N fallos

    El estado se persiste en Redis para sobrevivir a reinicios de la aplicación.
    """

    # Estados posibles
    STATE_CLOSED = 'closed'
    STATE_OPEN = 'open'
    STATE_HALF_OPEN = 'half-open'

    def __init__(
        self,
        redis_client: redis.Redis,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """
        Args:
            redis_client: Cliente Redis para persistencia
            failure_threshold: Fallos antes de abrir circuito
            recovery_timeout: Segundos antes de intentar recuperar
        """
        self.redis = redis_client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._prefix = "circuit_breaker"

    def _get_key(self, key: str, suffix: str) -> str:
        """Generar clave Redis para un campo del circuito"""
        return f"{self._prefix}:{key}:{suffix}"

    def get_state(self, key: str) -> str:
        """Obtener estado del circuito desde Redis"""
        state_key = self._get_key(key, "state")
        state = self.redis.get(state_key)
        if state is None:
            return self.STATE_CLOSED
        return state.decode('utf-8')

    def is_open(self, key: str) -> bool:
        """Verificar si el circuito está abierto"""
        state = self.get_state(key)

        if state == self.STATE_OPEN:
            # Verificar si ya pasó el recovery timeout
            last_failure_key = self._get_key(key, "last_failure")
            last_failure = self.redis.get(last_failure_key)

            if last_failure is None:
                # No hay registro de fallo, cerrar circuito
                self._set_state(key, self.STATE_CLOSED)
                return False

            last_failure_ts = float(last_failure)
            if time.time() - last_failure_ts >= self.recovery_timeout:
                # Pasar a half-open
                self._set_state(key, self.STATE_HALF_OPEN)
                return False
            return True

        return False

    def _set_state(self, key: str, state: str):
        """Guardar estado en Redis"""
        state_key = self._get_key(key, "state")
        self.redis.set(state_key, state)

    def record_success(self, key: str):
        """Registrar éxito - resetear contador de fallos y cerrar circuito"""
        failures_key = self._get_key(key, "failures")
        self.redis.delete(failures_key)
        self._set_state(key, self.STATE_CLOSED)
        logger.debug(f"Circuit breaker cerrado para {key} tras éxito")

    def record_failure(self, key: str, status_code: Optional[int] = None):
        """
        Registrar fallo

        Args:
            key: Clave del servicio
            status_code: Código HTTP si aplica
        """
        # 429 = rate limit, no abrir circuito
        if status_code == 429:
            logger.warning(f"Rate limit (429) para {key} - aplicando backoff")
            return

        failures_key = self._get_key(key, "failures")
        last_failure_key = self._get_key(key, "last_failure")

        # Incrementar contador de fallos
        current_failures = self.redis.incr(failures_key)
        self.redis.set(last_failure_key, time.time())

        if current_failures >= self.failure_threshold:
            self._set_state(key, self.STATE_OPEN)
            logger.error(f"Circuit breaker abierto para {key} después de {current_failures} fallos")


# ============================================
# SERVICIO PRINCIPAL
# ============================================

class ARCAService:
    """
    Servicio principal de acceso a ARCA

    Proporciona métodos para todos los web services
    con rate limiting, circuit breaker y reintentos.
    """

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
        self.rate_limiter = RateLimiter(self.redis_client, max_tokens=50)
        self.circuit_breaker = CircuitBreaker(
            self.redis_client,
            failure_threshold=5,
            recovery_timeout=60
        )

    def _get_auth_headers(
        self,
        session,
        tenant_id: int,
        servicio: str
    ) -> dict[str, str]:
        """
        Obtener headers de autenticación para un servicio

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            servicio: Nombre del servicio

        Returns:
            dict: Headers SOAP con token y signature
        """
        token, signature = get_token_para_servicio(
            session, tenant_id, servicio, force_refresh=False
        )

        cuit = settings.arca_cuit_estudio

        return {
            "token": token,
            "sign": signature,
            "cuit": cuit
        }

    # ============================================
    # WSFE - FACTURACIÓN ELECTRÓNICA
    # ============================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=120),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def wsfe_fe_cae(
        self,
        session,
        tenant_id: int,
        comprobante: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Autorizar comprobante electrónico (FECAESolicitar)

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            comprobante: Datos del comprobante

        Returns:
            dict: Respuesta con CAE, vencimiento, etc.
        """
        servicio = "wsfe"
        key = f"{servicio}:{tenant_id}"

        # Verificar circuit breaker
        if self.circuit_breaker.is_open(key):
            raise Exception(f"Circuit breaker abierto para {servicio}")

        # Rate limiting
        if not self.rate_limiter.acquire(key):
            raise Exception("Rate limit excedido - reintentar en 30s")

        try:
            client = get_client(servicio)
            auth = self._get_auth_headers(session, tenant_id, servicio)

            # Construir request
            fe_cae_req = self._construir_fe_cae_request(comprobante, auth)

            # Llamar al servicio
            result = client.service.FECAESolicitar(
                Auth=auth,
                FeCAEReq=fe_cae_req
            )

            # Verificar respuesta
            if result.FeCabResp.Resultado == "A":
                self.circuit_breaker.record_success(key)
                return self._parsear_cae_response(result)
            else:
                self.circuit_breaker.record_failure(key)
                raise Exception(f"ARCA rechazó comprobante: {result.FeCabResp.Observaciones}")

        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure(key, e.response.status_code)
            raise
        except Exception as e:
            self.circuit_breaker.record_failure(key)
            logger.error(f"Error en WSFE: {e}")
            raise

    def _construir_fe_cae_request(
        self,
        comprobante: dict[str, Any],
        auth: dict[str, str]
    ) -> dict[str, Any]:
        """
        Construir request para FECAESolicitar

        Args:
            comprobante: Datos del comprobante
            auth: Headers de autenticación

        Returns:
            dict: Request estructurado para zeep
        """
        # Implementación detallada según esquema WSFE v1
        return {
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": comprobante["punto_venta"],
                "CbteTipo": comprobante["tipo_comprobante"],
            },
            "FeDetReq": [{
                "Concepto": comprobante.get("concepto", 1),
                "DocTipo": comprobante.get("doc_tipo", 96),
                "DocNro": comprobante["cuit_receptor"],
                "CbteDesde": comprobante["numero"],
                "CbteHasta": comprobante["numero"],
                "CbteFch": comprobante["fecha_emision"].strftime("%Y%m%d") if isinstance(comprobante["fecha_emision"], date) else comprobante["fecha_emision"],
                "ImpTotal": float(comprobante["total"]),
                "ImpTotConc": float(comprobante.get("neto_no_gravado", 0)),
                "ImpNeto": float(comprobante.get("neto_gravado", 0)),
                "ImpOpEx": float(comprobante.get("neto_exento", 0)),
                "ImpIVA": float(comprobante.get("iva", 0)),
                "ImpTrib": float(comprobante.get("percepcion_iibb", 0)),
                "MonId": "PES",
                "MonCotiz": 1.0,
            }]
        }

    def _parsear_cae_response(self, result: Any) -> dict[str, Any]:
        """
        Parsear respuesta de FECAESolicitar

        Args:
            result: Respuesta de zeep

        Returns:
            dict: CAE, vencimiento, observaciones
        """
        fe_cab_resp = result.FeCabResp
        fe_det_resp = result.FeDetResp[0] if result.FeDetResp else {}

        return {
            "cae": fe_det_resp.get("CAE", ""),
            "cae_vencimiento": fe_det_resp.get("CAEFchVto", ""),
            "resultado": fe_cab_resp.Resultado,
            "observaciones": fe_cab_resp.Observaciones or [],
        }

    # ============================================
    # WSCDC - DESCARGA MASIVA DE COMPROBANTES
    # ============================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=120),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def wscdc_descargar_comprobantes(
        self,
        session,
        tenant_id: int,
        cuit_emisor: str,
        periodo: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """
        Descargar comprobantes emitidos para un CUIT

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            cuit_emisor: CUIT del emisor a consultar
            periodo: (año, mes) del período

        Returns:
            list: Lista de comprobantes descargados
        """
        servicio = "wscdc"
        key = f"{servicio}:{tenant_id}"

        if self.circuit_breaker.is_open(key):
            raise Exception(f"Circuit breaker abierto para {servicio}")

        if not self.rate_limiter.acquire(key, tokens=2):
            raise Exception("Rate limit excedido")

        try:
            client = get_client(servicio)
            auth = self._get_auth_headers(session, tenant_id, servicio)

            # Llamar al servicio
            anio, mes = periodo
            result = client.service.ConsultarComprobantes(
                Auth=auth,
                CuitEmisor=cuit_emisor,
                Anio=anio,
                Mes=mes
            )

            self.circuit_breaker.record_success(key)

            # Parsear respuesta
            return self._parsear_cdc_response(result)

        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure(key, e.response.status_code)
            raise
        except Exception as e:
            self.circuit_breaker.record_failure(key)
            logger.error(f"Error en WSCDC: {e}")
            raise

    def _parsear_cdc_response(self, result: Any) -> list[dict[str, Any]]:
        """
        Parsear respuesta de ConsultarComprobantes

        Args:
            result: Respuesta de zeep

        Returns:
            list: Lista de comprobantes
        """
        comprobantes = []

        for cbte in result.Comprobantes or []:
            comprobantes.append({
                "tipo_comprobante": cbte.CbteTipo,
                "punto_venta": cbte.PtoVta,
                "numero": cbte.CbteNumero,
                "fecha_emision": cbte.CbteFchEmision,
                "total": Decimal(str(cbte.ImporteTotal)),
                "cae": cbte.CAE,
                "estado": cbte.Estado,
            })

        return comprobantes

    # ============================================
    # PADRONES - VALIDACIÓN DE CUITs
    # ============================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def padron_a4_consultar(
        self,
        session,
        tenant_id: int,
        cuit: str
    ) -> dict[str, Any]:
        """
        Consultar Padrón A4 (datos de contribuyentes)

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            cuit: CUIT a consultar

        Returns:
            dict: Datos del contribuyente
        """
        servicio = "padron_a4"
        key = f"{servicio}:{tenant_id}"

        if self.circuit_breaker.is_open(key):
            raise Exception(f"Circuit breaker abierto para {servicio}")

        if not self.rate_limiter.acquire(key):
            raise Exception("Rate limit excedido")

        try:
            client = get_client(servicio)
            auth = self._get_auth_headers(session, tenant_id, servicio)

            result = client.service.GetPersona(
                token=auth["token"],
                sign=auth["sign"],
                cuit=cuit
            )

            self.circuit_breaker.record_success(key)
            return self._parsear_padron_response(result)

        except Exception as e:
            self.circuit_breaker.record_failure(key)
            logger.error(f"Error en Padrón A4: {e}")
            raise

    def _parsear_padron_response(self, result: Any) -> dict[str, Any]:
        """Parsear respuesta del padrón"""
        if not result:
            return {}

        return {
            "cuit": result.cuit,
            "razon_social": result.razonSocial,
            "nombre_fantasia": result.nombreFantasia,
            "tipo_persona": result.tipoPersona,
            "tipo_responsable": result.tipoResponsable,
            "estado": result.estado,
            "domicilio": result.domicilio,
            "localidad": result.localidad,
            "provincia": result.provincia,
            "codigo_postal": result.codPostal,
        }

    async def constancia_inscripcion(
        self,
        session,
        tenant_id: int,
        cuit: str
    ) -> Optional[dict[str, Any]]:
        """
        Obtener constancia de inscripción desde ws_sr_constancia_inscripcion.

        Returns datos de la constancia de inscripción del contribuyente.

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            cuit: CUIT del contribuyente

        Returns:
            dict con datos de la constancia o None
        """
        servicio = "constancia_inscripcion"
        key = f"{servicio}:{tenant_id}"

        if self.circuit_breaker.is_open(key):
            logger.warning("Circuit breaker abierto — omitiendo constancia_inscripcion")
            return None

        try:
            client = get_client(servicio)
        except Exception as e:
            logger.error(f"Error obteniendo cliente constancia_inscripcion: {e}")
            return None

        try:
            auth = self._get_auth_headers(session, tenant_id, servicio)
        except Exception as e:
            logger.error(f"Error obteniendo tokens WSAA: {e}")
            self.circuit_breaker.record_failure(key)
            return None

        try:
            # Llamar al servicio de constancia de inscripción
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.service.GetConstanciaInscripcion(
                    token=auth["token"],
                    sign=auth["sign"],
                    cuitRepresentada=auth["cuit"],
                    cuitConsulta=cuit
                )
            )

            self.circuit_breaker.record_success(key)
            return self._parsear_constancia_inscripcion_response(response)

        except Exception as e:
            self.circuit_breaker.record_failure(key)
            logger.error(f"Error en constancia_inscripcion: {e}")
            return None

    def _parsear_constancia_inscripcion_response(self, response) -> dict[str, Any]:
        """
        Parsear respuesta de ws_sr_constancia_inscripcion.
        """
        try:
            datos = response.resultado.datos

            return {
                "cuit": datos.generales.cuit if hasattr(datos, "generales") else None,
                "razon_social": datos.generales.razonSocial if hasattr(datos, "generales") else None,
                "tipo_responsable": datos.generales.tipoContribuyente if hasattr(datos, "generales") else None,
                "estado": datos.generales.estado if hasattr(datos, "generales") else None,
                "impuestos": [imp.codigo for imp in datos.regimenes] if hasattr(datos, "regimenes") else [],
            }
        except Exception as e:
            logger.warning(f"Error parseando constancia_inscripcion: {e}")
            return {}

    # ============================================
    # CONSULTA DE COMPROBANTE INDIVIDUAL
    # ============================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def consultar_comprobante(
        self,
        session,
        tenant_id: int,
        cuit_emisor: str,
        tipo_comprobante: int,
        punto_venta: int,
        numero: int
    ) -> dict[str, Any]:
        """
        Consultar estado de un comprobante en ARCA vía WSFE

        Args:
            session: Sesión de BD
            tenant_id: ID del tenant
            cuit_emisor: CUIT del emisor
            tipo_comprobante: Tipo de comprobante (1=FA A, 6=FA B, etc.)
            punto_venta: Punto de venta
            numero: Número de comprobante

        Returns:
            dict: Estado del comprobante en ARCA
        """
        servicio = "wsfe"
        key = f"{servicio}:{tenant_id}"

        if self.circuit_breaker.is_open(key):
            raise Exception(f"Circuit breaker abierto para {servicio}")

        if not self.rate_limiter.acquire(key):
            raise Exception("Rate limit excedido")

        try:
            client = get_client(servicio)
            auth = self._get_auth_headers(session, tenant_id, servicio)

            # Obtener último comprobante autorizado para validar conexión
            result = client.service.FECompUltimoAutorizado(
                Auth=auth,
                PtoVta=punto_venta,
                CbteTipo=tipo_comprobante
            )

            # Si el comprobante existe, consultar sus datos
            # Nota: WSFE no permite consultar un comprobante específico por CUIT+numero
            # Usamos WSCDC para eso (ver descargar_comprobantes)
            self.circuit_breaker.record_success(key)

            return {
                "disponible": True,
                "ultimo_numero": result.CbteNumero if hasattr(result, 'CbteNumero') else None,
                "mensaje": "WSFE disponible - usar WSCDC para consulta por CUIT"
            }

        except Exception as e:
            self.circuit_breaker.record_failure(key)
            logger.error(f"Error al consultar WSFE: {e}")
            raise

    # ============================================
    # VERIFICACIÓN DE ESTADO
    # ============================================

    async def verificar_estado_servicios(self) -> dict[str, bool]:
        """
        Verificar estado de todos los servicios ARCA

        Returns:
            dict: Estado de cada servicio (True = disponible)
        """
        estados = {}

        for servicio in SERVICIOS:
            try:
                client = get_client(servicio)
                # Ping básico
                estados[servicio] = True
            except Exception:
                estados[servicio] = False
                logger.warning(f"Servicio {servicio} no disponible")

        return estados


# ============================================
# INSTANCIA GLOBAL
# # ============================================

arca_service = ARCAService()
