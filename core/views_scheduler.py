"""
Views para gerenciar o scheduler via interface web
Opcional - você pode usar via linha de comando se preferir
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from core.scheduler import AgendadorSincronizacao, SincronizadorAPI
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def iniciar_scheduler(request):
    """Inicia o scheduler"""
    try:
        AgendadorSincronizacao.iniciar()
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Scheduler iniciado com sucesso'
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def parar_scheduler(request):
    """Para o scheduler"""
    try:
        AgendadorSincronizacao.parar()
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Scheduler parado com sucesso'
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def sincronizar_agora(request):
    """Força uma sincronização imediata"""
    try:
        AgendadorSincronizacao.sincronizar_agora()
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Sincronização executada com sucesso'
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def status_scheduler(request):
    """Retorna o status do scheduler"""
    try:
        status = AgendadorSincronizacao.obter_status()
        config = SincronizadorAPI.CONFIG
        
        return JsonResponse({
            'sucesso': True,
            'scheduler': status,
            'configuracao': {
                'url_base': config['url_base'],
                'intervalo_minutos': config['intervalo_minutos'],
                'paginacoes': config['paginacoes'],
                'ativo': config['ativo'],
            }
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)
