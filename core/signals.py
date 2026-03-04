"""
Signals para sincronização automática do scheduler quando agendamentos são modificados
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import AgendamentoSincronizacao

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AgendamentoSincronizacao)
def recarregar_scheduler_ao_salvar(sender, instance, created, **kwargs):
    """Recarrega o scheduler automaticamente quando um agendamento é criado/modificado"""
    try:
        from core.scheduler import AgendadorSincronizacao
        
        acao = "criado" if created else "modificado"
        logger.info(f"Agendamento '{instance.nome}' foi {acao}. Recarregando scheduler...")
        
        AgendadorSincronizacao.recarregar_agendamentos()
        logger.info(f"[OK] Scheduler recarregado com sucesso apos {acao} o agendamento '{instance.nome}'")
        
    except Exception as e:
        logger.error(f"[ERRO] Falha ao recarregar scheduler apos salvar agendamento: {str(e)}")


@receiver(post_delete, sender=AgendamentoSincronizacao)
def recarregar_scheduler_ao_deletar(sender, instance, **kwargs):
    """Recarrega o scheduler automaticamente quando um agendamento é deletado"""
    try:
        from core.scheduler import AgendadorSincronizacao
        
        logger.info(f"Agendamento '{instance.nome}' foi deletado. Recarregando scheduler...")
        
        AgendadorSincronizacao.recarregar_agendamentos()
        logger.info(f"[OK] Scheduler recarregado com sucesso apos deletar o agendamento '{instance.nome}'")
        
    except Exception as e:
        logger.error(f"[ERRO] Falha ao recarregar scheduler apos deletar agendamento: {str(e)}")
