import requests
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sincronizar_pedidos_da_api(self):
    """
    Task Celery para sincronizar pedidos da API a cada 5 minutos
    """
    try:
        logger.info(f"[{timezone.now()}] Iniciando sincronização de pedidos da API...")
        
        # Chamar o comando de management
        call_command('sincronizar_api_pedidos', pagina=1, tamanho=50, verbosity=2)
        
        logger.info(f"[{timezone.now()}] ✅ Sincronização concluída com sucesso!")
        return {"status": "sucesso", "timestamp": str(timezone.now())}
        
    except Exception as exc:
        logger.error(f"Erro na sincronização: {str(exc)}")
        # Retry com backoff exponencial (5s, 25s, 125s)
        raise self.retry(exc=exc, countdown=5 ** self.request.retries)


@shared_task
def sincronizar_multiplas_paginas(total_paginas=10):
    """
    Task para sincronizar múltiplas páginas da API
    Útil para sincronização inicial ou limpeza completa
    """
    try:
        logger.info(f"Iniciando sincronização de {total_paginas} páginas...")
        
        for pagina in range(1, total_paginas + 1):
            logger.info(f"Sincronizando página {pagina}/{total_paginas}...")
            call_command('sincronizar_api_pedidos', pagina=pagina, tamanho=50, verbosity=1)
        
        logger.info("✅ Sincronização de múltiplas páginas concluída!")
        return {"status": "sucesso", "paginas": total_paginas}
        
    except Exception as e:
        logger.error(f"Erro na sincronização de múltiplas páginas: {str(e)}")
        raise
