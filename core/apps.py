import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Inicializa o scheduler quando a app é carregada"""
        try:
            from core.scheduler import AgendadorSincronizacao, SincronizadorAPI
            
            # Verifica se o scheduler deve ser iniciado automaticamente
            if SincronizadorAPI.CONFIG['ativo']:
                # Apenas inicia se não estiver rodando em modo de migração
                import sys
                if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
                    AgendadorSincronizacao.iniciar()
                    logger.info("Scheduler de sincronização iniciado automaticamente")
        except Exception as e:
            logger.error(f"Erro ao inicializar scheduler: {str(e)}")
