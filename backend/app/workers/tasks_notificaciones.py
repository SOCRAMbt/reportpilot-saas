"""
Tareas Celery para notificaciones (WhatsApp, Email, Portal)

Implementa envío real de emails vía SMTP.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery import shared_task
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


def _enviar_email(
    destinatario: str,
    asunto: str,
    cuerpo_html: str,
    cuerpo_texto: Optional[str] = None
) -> bool:
    """
    Enviar email vía SMTP

    Args:
        destinatario: Email del destinatario
        asunto: Asunto del email
        cuerpo_html: Cuerpo en formato HTML
        cuerpo_texto: Cuerpo en texto plano (opcional)

    Returns:
        bool: True si se envió correctamente
    """
    if not settings.smtp_host or not settings.smtp_port:
        logger.warning("SMTP no configurado - email no enviado")
        return False

    # Construir mensaje
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = destinatario

    # Adjuntar versiones texto y HTML
    if cuerpo_texto:
        msg.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        # Conectar y enviar
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port)

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(settings.smtp_from or settings.smtp_user, destinatario, msg.as_string())
        server.quit()

        logger.info(f"Email enviado a {destinatario}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar email: {e}")
        return False


@shared_task
def enviar_notificacion_vep(vep_id: int, cliente_email: str, cliente_nombre: str = "Cliente",
                           importe: float = 0, periodo: str = "", tipo_vep: str = ""):
    """
    Notificar al cliente sobre VEP pre-liquidado

    Envía email con enlace al portal seguro para aprobación.
    """
    logger.info(f"Notificando VEP {vep_id} a {cliente_email}")

    asunto = f"AccountantOS - Nueva obligación fiscal para aprobar ({periodo})"

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a365d; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f7fafc; padding: 30px; border: 1px solid #e2e8f0; }}
            .button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 24px;
                       text-decoration: none; border-radius: 6px; margin-top: 20px; }}
            .footer {{ font-size: 12px; color: #718096; padding: 20px; text-align: center; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #2d3748; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AccountantOS</h1>
            </div>
            <div class="content">
                <p>Hola {cliente_nombre},</p>
                <p>Tu estudio contable ha pre-liquidado una nueva obligación fiscal:</p>
                <table style="width: 100%; margin: 20px 0;">
                    <tr>
                        <td><strong>Concepto:</strong></td>
                        <td>{tipo_vep or "Obligación Fiscal"}</td>
                    </tr>
                    <tr>
                        <td><strong>Período:</strong></td>
                        <td>{periodo or "N/A"}</td>
                    </tr>
                    <tr>
                        <td><strong>Importe:</strong></td>
                        <td class="amount">${importe:,.2f}</td>
                    </tr>
                </table>
                <p>Para revisar los detalles y aprobar el pago, ingresá al portal:</p>
                <a href="{settings.frontend_url}/portal/veps/{vep_id}" class="button">
                    Ver y Aprobar VEP
                </a>
                <p style="margin-top: 20px; font-size: 14px; color: #718096;">
                    ⚠️ El vencimiento es próximo. Aprobá antes de la fecha límite para evitar recargos.
                </p>
            </div>
            <div class="footer">
                <p>Este es un mensaje automático de AccountantOS.</p>
                <p>Si tenés dudas, contactá a tu estudio contable.</p>
            </div>
        </div>
    </body>
    </html>
    """

    cuerpo_texto = f"""
    Hola {cliente_nombre},

    Tu estudio contable ha pre-liquidado una nueva obligación fiscal:

    Concepto: {tipo_vep or "Obligación Fiscal"}
    Período: {periodo or "N/A"}
    Importe: ${importe:,.2f}

    Para revisar los detalles y aprobar el pago, ingresá al portal:
    {settings.frontend_url}/portal/veps/{vep_id}

    ⚠️ El vencimiento es próximo. Aprobá antes de la fecha límite.

    --
    AccountantOS
    """

    exito = _enviar_email(cliente_email, asunto, cuerpo_html, cuerpo_texto)

    if exito:
        logger.info(f"Notificación VEP {vep_id} enviada a {cliente_email}")
    else:
        logger.error(f"Falló envío de notificación VEP {vep_id}")

    return exito


@shared_task
def enviar_alerta_urgente(usuario_id: int, usuario_email: str, usuario_nombre: str,
                         alerta_titulo: str, alerta_mensaje: str, prioridad: str = "alta"):
    """
    Enviar alerta urgente al contador

    Args:
        usuario_id: ID del usuario
        usuario_email: Email del usuario
        usuario_nombre: Nombre del usuario
        alerta_titulo: Título de la alerta
        alerta_mensaje: Mensaje detallado
        prioridad: Nivel de prioridad (baja, media, alta, critica)
    """
    logger.info(f"Enviando alerta urgente a usuario {usuario_id}")

    icono_prioridad = {"baja": "ℹ️", "media": "⚠️", "alta": "🔴", "critica": "🚨"}
    color_prioridad = {"baja": "#718096", "media": "#d69e2e", "alta": "#e53e3e", "critica": "#c53030"}

    asunto = f"🚨 AccountantOS - {alerta_titulo}"

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: {color_prioridad.get(prioridad, '#e53e3e')}; color: white;
                       padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #fff5f5; padding: 30px; border: 1px solid #fc8181; }}
            .button {{ display: inline-block; background: #e53e3e; color: white; padding: 12px 24px;
                       text-decoration: none; border-radius: 6px; margin-top: 20px; }}
            .footer {{ font-size: 12px; color: #718096; padding: 20px; text-align: center; }}
            .alert-icon {{ font-size: 48px; text-align: center; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{icono_prioridad.get(prioridad, '🚨')} Alerta de AccountantOS</h1>
            </div>
            <div class="content">
                <div class="alert-icon">{icono_prioridad.get(prioridad, '🚨')}</div>
                <h2>{alerta_titulo}</h2>
                <p>{alerta_mensaje}</p>
                <a href="{settings.frontend_url}/alertas" class="button">
                    Ver Alertas en el Sistema
                </a>
            </div>
            <div class="footer">
                <p>Este es un mensaje automático de AccountantOS.</p>
                <p>Prioridad: {prioridad.upper()}</p>
            </div>
        </div>
    </body>
    </html>
    """

    cuerpo_texto = f"""
    🚨 ALERTA URGENTE - AccountantOS

    {alerta_titulo}

    {alerta_mensaje}

    Prioridad: {prioridad.upper()}

    Ver alertas en el sistema:
    {settings.frontend_url}/alertas

    --
    AccountantOS
    """

    exito = _enviar_email(usuario_email, asunto, cuerpo_html, cuerpo_texto)

    if exito:
        logger.info(f"Alerta urgente enviada a usuario {usuario_id}")
    else:
        logger.error(f"Falló envío de alerta urgente a usuario {usuario_id}")

    return exito


@shared_task
def recordar_vencimiento_vep(vep_id: int, cliente_email: str, cliente_nombre: str,
                            fecha_vencimiento: str, importe: float, periodo: str):
    """
    Recordar vencimiento de VEP (2 días antes)

    Args:
        vep_id: ID del VEP
        cliente_email: Email del cliente
        cliente_nombre: Nombre del cliente
        fecha_vencimiento: Fecha de vencimiento (YYYY-MM-DD)
        importe: Importe a pagar
        periodo: Período fiscal
    """
    logger.info(f"Recordando vencimiento VEP {vep_id}")

    asunto = f"⏰ Recordatorio: Vencimiento de obligación fiscal ({periodo})"

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2c5282; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #ebf8ff; padding: 30px; border: 1px solid #bee3f8; }}
            .button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 24px;
                       text-decoration: none; border-radius: 6px; margin-top: 20px; }}
            .footer {{ font-size: 12px; color: #718096; padding: 20px; text-align: center; }}
            .warning {{ background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0;
                        border-left: 4px solid #d69e2e; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #2d3748; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⏰ Recordatorio de Vencimiento</h1>
            </div>
            <div class="content">
                <p>Hola {cliente_nombre},</p>
                <p>Te recordamos que está por vencer la siguiente obligación fiscal:</p>
                <table style="width: 100%; margin: 20px 0;">
                    <tr>
                        <td><strong>Concepto:</strong></td>
                        <td>Obligación Fiscal - {periodo}</td>
                    </tr>
                    <tr>
                        <td><strong>Importe:</strong></td>
                        <td class="amount">${importe:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Vencimiento:</strong></td>
                        <td style="color: #e53e3e; font-weight: bold;">{fecha_vencimiento}</td>
                    </tr>
                </table>
                <div class="warning">
                    <strong>⚠️ Importante:</strong> Si ya realizaste el pago, ignorá este mensaje.
                </div>
                <a href="{settings.frontend_url}/portal/veps" class="button">
                    Ver Obligaciones Pendientes
                </a>
            </div>
            <div class="footer">
                <p>Este es un mensaje automático de AccountantOS.</p>
            </div>
        </div>
    </body>
    </html>
    """

    cuerpo_texto = f"""
    ⏰ Recordatorio de Vencimiento - AccountantOS

    Hola {cliente_nombre},

    Te recordamos que está por vencer la siguiente obligación fiscal:

    Concepto: Obligación Fiscal - {periodo}
    Importe: ${importe:,.2f}
    Vencimiento: {fecha_vencimiento}

    ⚠️ Importante: Si ya realizaste el pago, ignorá este mensaje.

    Ver obligaciones pendientes:
    {settings.frontend_url}/portal/veps

    --
    AccountantOS
    """

    exito = _enviar_email(cliente_email, asunto, cuerpo_html, cuerpo_texto)

    if exito:
        logger.info(f"Recordatorio de vencimiento VEP {vep_id} enviado a {cliente_email}")
    else:
        logger.error(f"Falló envío de recordatorio VEP {vep_id}")

    return exito


@shared_task
def notificar_vencimiento_whatsapp(vep_id: int, cliente_telefono: str, cliente_nombre: str,
                                   fecha_vencimiento: str, periodo: str):
    """
    Enviar recordatorio de vencimiento por WhatsApp.
    NUNCA incluir importes (ver especificación de seguridad).
    """
    from app.core.config import settings

    if not settings.whatsapp_phone_id or not settings.whatsapp_access_token:
        logger.warning("WhatsApp no configurado — omitiendo notificación")
        return False

    import httpx

    url = f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_id}/messages"
    mensaje = (
        f"Hola {cliente_nombre}, te recordamos que tenés una obligación fiscal "
        f"que vence el {fecha_vencimiento} ({periodo}). "
        f"Ingresá al portal para ver los detalles y aprobar el pago."
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": cliente_telefono,
        "type": "text",
        "text": {"body": mensaje}
    }
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    async def enviar():
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            return response.status_code == 200

    import asyncio
    try:
        ok = asyncio.run(enviar())
        if ok:
            logger.info(f"WhatsApp enviado a {cliente_telefono} para VEP {vep_id}")
        else:
            logger.error(f"Falló envío WhatsApp para VEP {vep_id}")
        return ok
    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        return False
