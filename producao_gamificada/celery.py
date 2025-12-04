import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'producao_gamificada.settings')

app = Celery('producao_gamificada')

# Carregar configurações do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobrir tasks automaticamente
app.autodiscover_tasks()

# Configurar Celery Beat Schedule
app.conf.beat_schedule = {
    'sincronizar-pedidos-a-cada-5-minutos': {
        'task': 'core.tasks.sincronizar_pedidos_da_api',
        'schedule': 300.0,  # 5 minutos = 300 segundos
        'options': {'queue': 'default'}
    },
}
