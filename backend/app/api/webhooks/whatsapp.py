"""
Webhook de WhatsApp Business API — Recepción de mensajes e imágenes

Cuando un cliente envía una foto de factura por WhatsApp, este endpoint
la recibe, la almacena temporalmente y la envía al pipeline OCR para
extracción automática de datos.
"""
import hashlib
import hmac
import logging
from pathlib import Path
from datetime import datetime

import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["Webhooks WhatsApp"])


@router.get("/verify")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Verificación del webhook por Meta (WhatsApp Business API).
    Se ejecuta una sola vez al configurar el webhook.
    """
    if mode == "subscribe" and token == settings.whatsapp_webhook_secret:
        logger.info("Webhook de WhatsApp verificado correctamente")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("")
async def recibir_mensaje(request: Request):
    """
    Recibe mensajes entrantes de WhatsApp Business API.
    
    Si el mensaje contiene una imagen (factura física fotografiada),
    la descarga y la envía al pipeline OCR para extracción de datos.
    """
    body = await request.json()

    # Validar firma HMAC si está configurada
    if settings.whatsapp_webhook_secret:
        x_signature = request.headers.get("X-Hub-Signature-256", "")
        if x_signature:
            expected = hmac.new(
                settings.whatsapp_webhook_secret.encode(),
                await request.body(),
                hashlib.sha256,
            ).hexdigest()
            if x_signature != f"sha256={expected}":
                logger.warning("Firma HMAC inválida en webhook de WhatsApp")
                raise HTTPException(status_code=401, detail="Firma inválida")

    # Procesar mensajes entrantes
    try:
        entry = body.get("entry", [])
        for entry_item in entry:
            changes = entry_item.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    await _procesar_mensaje(message, value)

        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _procesar_mensaje(message: dict, value: dict):
    """Procesa un mensaje individual de WhatsApp."""
    from_id = message.get("from", "")
    msg_type = message.get("type", "")

    logger.info(f"Mensaje de {from_id[:4]}*** tipo={msg_type}")

    if msg_type == "image":
        # Descargar imagen y procesar con OCR
        image_data = message.get("image", {})
        image_id = image_data.get("id", "")
        caption = image_data.get("caption", "")

        if image_id:
            await _descargar_y_procesar_ocr(image_id, from_id, caption)


async def _descargar_y_procesar_ocr(image_id: str, from_id: str, caption: str):
    """Descarga imagen de WhatsApp y la envía al OCR."""
    if not settings.whatsapp_access_token:
        logger.warning("WhatsApp access token no configurado — omitiendo descarga")
        return

    # 1. Obtener URL de la imagen
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://graph.facebook.com/v18.0/{image_id}",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )
        if r.status_code != 200:
            logger.error(f"No se pudo obtener URL de imagen {image_id}: {r.status_code}")
            return

        image_url = r.json().get("url", "")

        # 2. Descargar imagen
        r = await client.get(
            image_url,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )
        if r.status_code != 200:
            logger.error(f"No se pudo descargar imagen {image_id}: {r.status_code}")
            return

        image_bytes = r.content

    # 3. Guardar temporalmente
    upload_dir = Path("/tmp/accountantos_whatsapp")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / f"{from_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path.write_bytes(image_bytes)

    logger.info(f"Imagen guardada: {file_path} — lista para OCR")

    # 4. Enviar al OCR (si está disponible)
    try:
        from app.services.ocr import procesar_comprobante_ocr
        # Usar tenant_id=1 (persona física)
        resultado = await procesar_comprobante_ocr(1, image_bytes)
        logger.info(f"OCR completado: {resultado.to_dict()}")

        # 5. Notificar resultado al cliente
        await _enviar_respuesta_whatsapp(from_id, resultado)
    except Exception as e:
        logger.error(f"Error en OCR para imagen de WhatsApp: {e}")
        await _enviar_error_whatsapp(from_id, str(e))


async def _enviar_respuesta_whatsapp(to: str, resultado):
    """Envía confirmación al cliente de que la factura fue procesada."""
    if not settings.whatsapp_phone_id or not settings.whatsapp_access_token:
        return

    msg = (
        "✅ Factura recibida y procesada correctamente.\n"
        "Los datos fueron extraídos y están disponibles en el sistema.\n"
        "Si detectás algún error, contactá a tu contadora."
    )
    await _enviar_texto_whatsapp(to, msg)


async def _enviar_error_whatsapp(to: str, error: str):
    """Notifica al cliente que hubo un error procesando la imagen."""
    msg = (
        "⚠️ No pudimos procesar la imagen de la factura.\n"
        "Intentá sacar una foto más clara o enviala directamente por el sistema.\n"
        "Si el problema persiste, contactá a tu contadora."
    )
    await _enviar_texto_whatsapp(to, msg)


async def _enviar_texto_whatsapp(to: str, texto: str):
    """Envía un mensaje de texto por WhatsApp."""
    if not settings.whatsapp_phone_id or not settings.whatsapp_access_token:
        return

    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": texto},
                },
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Error enviando WhatsApp a {to[:4]}***: {e}")
