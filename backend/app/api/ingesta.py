"""
API de Ingesta de Fotos — Recepción de facturas por imagen/WhatsApp
"""
import logging
from pathlib import Path
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import Comprobante, Cliente
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingesta", tags=["Ingesta de Facturas"])

# Directorio temporal para imágenes subidas
UPLOAD_DIR = Path("/tmp/accountantos_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/foto")
async def recibir_factura_foto(
    archivo: UploadFile = File(description="Foto de la factura (jpg/png/pdf)"),
    cliente_id: int = Form(description="ID del cliente al que pertenece"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Recibir foto de factura y procesarla con OCR.

    - Si confidence >= 95%: crea comprobante automático (INCORPORADO)
    - Si confidence < 95%: crea comprobante con estado REVISION_HUMANA
    - Si OCR no disponible: crea comprobante vacío para completar manual

    Retorna:
    - comprobante_id: ID del comprobante creado
    - datos_ocr: datos extraídos (pueden estar vacíos)
    - confidence: score de confianza (0-100)
    - requiere_revision: true si necesita revisión humana
    """
    # Verificar cliente
    cliente = await db.get(Cliente, cliente_id)
    if not cliente or cliente.tenant_id != tenant_id:
        raise HTTPException(404, "Cliente no encontrado")

    # Leer archivo
    content = await archivo.read()
    if not content:
        raise HTTPException(400, "Archivo vacío")

    # Intentar OCR
    datos_ocr = {}
    confidence = 0
    requiere_revision = True

    try:
        from app.services.ocr import procesar_comprobante_ocr
        resultado = await procesar_comprobante_ocr(tenant_id, content)
        valido, errores = resultado.validar()

        if valido:
            datos_ocr = resultado.to_dict()
            # Calcular confidence promedio
            confs = resultado.confidence.values() if resultado.confidence else []
            confidence = int(sum(confs) / len(confs) * 100) if confs else 0
            requiere_revision = confidence < 95 or bool(resultado.texto_sospechoso_detectado)
        else:
            requiere_revision = True
            logger.warning(f"OCR inválido para cliente {cliente_id}: {errores}")

    except ImportError:
        logger.warning("OCR no disponible — creando comprobante manual")
        requiere_revision = True
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        requiere_revision = True

    # Crear comprobante
    from app.services.delta_processing import calcular_hash_delta

    cuit_emisor = datos_ocr.get("cuit_emisor", "")
    punto_venta = datos_ocr.get("punto_venta", 0) or 0
    numero = datos_ocr.get("numero", 0) or 0

    hash_delta = calcular_hash_delta(
        cuit_emisor or str(cliente.cuit),
        punto_venta,
        numero,
    )

    comprobante = Comprobante(
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        tipo_comprobante=datos_ocr.get("tipo_comprobante", ""),
        punto_venta=punto_venta,
        numero=numero,
        cuit_emisor=cuit_emisor,
        fecha_emision=_parsear_fecha(datos_ocr.get("fecha_emision")),
        total=datos_ocr.get("total", 0) or 0,
        neto_gravado=datos_ocr.get("neto_gravado", 0) or 0,
        iva=datos_ocr.get("iva", 0) or 0,
        cae=datos_ocr.get("cae", ""),
        estado_interno="INCORPORADO" if not requiere_revision else "REVISION_HUMANA",
        estado_arca="PENDIENTE",
        origen="ingesta_foto",
        hash_delta=hash_delta,
        observaciones="Subido por foto" + (" (revisión requerida)" if requiere_revision else ""),
    )

    db.add(comprobante)
    await db.commit()
    await db.refresh(comprobante)

    estado = "auto_aprobado" if not requiere_revision else "requiere_revision"
    logger.info(f"Factura ingesta: cliente={cliente_id}, id={comprobante.id}, estado={estado}, confidence={confidence}")

    return {
        "status": "ok",
        "comprobante_id": comprobante.id,
        "estado": estado,
        "datos_ocr": datos_ocr,
        "confidence": confidence,
        "requiere_revision": requiere_revision,
    }


def _parsear_fecha(fecha_str: str | None) -> date | None:
    """Parsear fecha del OCR (YYYY-MM-DD)"""
    if not fecha_str:
        return None
    try:
        return date.fromisoformat(fecha_str)
    except (ValueError, TypeError):
        return None
