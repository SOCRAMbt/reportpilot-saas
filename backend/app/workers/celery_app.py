"""
Configuración de Celery para tareas asíncronas
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# ============================================
# CONFIGURACIÓN DE CELERY
# ============================================

celery_app = Celery(
    "accountantos",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks_arca",
        "app.workers.tasks_fiscales",
        "app.workers.tasks_notificaciones",
    ]
)

# Configuración adicional
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutos máximo por tarea
    worker_prefetch_multiplier=1,
)

# ============================================
# TAREAS PROGRAMADAS (Celery Beat)
# ============================================

celery_app.conf.beat_schedule = {
    # Descarga masiva de comprobantes (ventana nocturna 02:00-05:00)
    "descarga-masiva-comprobantes": {
        "task": "app.workers.tasks_arca.descargar_comprobantes_nocturno",
        "schedule": crontab(hour='2,3,4', minute=0),
        "options": {"queue": "arca"},
    },

    # Re-verificación T+7 (diario a las 06:00)
    "re-verificacion-t7": {
        "task": "app.workers.tasks_arca.ejecutar_re_verificaciones",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "arca"},
    },

    # Pre-liquidación de VEPs
    "pre-liquidar-veps": {
        "task": "app.workers.tasks_fiscales.pre_liquidar_veps_mes",
        "schedule": crontab(hour=6, day_of_month="13,21,23"),
        "options": {"queue": "fiscales"},
    },

    # Análisis de riesgo fiscal
    "analisis-riesgo-fiscal": {
        "task": "app.workers.tasks_fiscales.analizar_riesgo_fiscal_cartera",
        "schedule": 60.0 * 60 * 24,  # Diario
        "options": {"queue": "fiscales"},
    },

    # Limpieza de tokens WSAA expirados
    "limpieza-tokens-wsaa": {
        "task": "app.workers.tasks_arca.limpieza_tokens_wsaa",
        "schedule": 60.0 * 30,  # Cada 30 minutos
        "options": {"queue": "arca"},
    },

    # Notificación de vencimientos por WhatsApp (diaria a las 09:00)
    "notificar-vencimientos-whatsapp": {
        "task": "app.workers.tasks_notificaciones.notificar_vencimiento_whatsapp",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "default"},
    },
}
