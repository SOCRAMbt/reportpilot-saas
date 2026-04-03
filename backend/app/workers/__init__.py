"""
Workers Celery de AccountantOS
"""

from app.workers.celery_app import celery_app
from app.workers.tasks_arca import *
from app.workers.tasks_fiscales import *
from app.workers.tasks_notificaciones import *
