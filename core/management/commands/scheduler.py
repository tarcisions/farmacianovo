"""
Comando Django para gerenciar o scheduler de sincronização
Uso: python manage.py scheduler [start|stop|status|agora]
"""

from django.core.management.base import BaseCommand
from core.scheduler import AgendadorSincronizacao, SincronizadorAPI
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Gerencia o scheduler de sincronização automática da API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'acao',
            nargs='?',
            default='status',
            choices=['start', 'stop', 'status', 'agora'],
            help='Ação a executar (start, stop, status, agora)'
        )
    
    def handle(self, *args, **options):
        acao = options['acao']
        
        if acao == 'start':
            self.stdout.write(self.style.SUCCESS('Iniciando scheduler...'))
            AgendadorSincronizacao.iniciar()
            self.stdout.write(self.style.SUCCESS('✓ Scheduler iniciado com sucesso!'))
            
        elif acao == 'stop':
            self.stdout.write(self.style.WARNING('Parando scheduler...'))
            AgendadorSincronizacao.parar()
            self.stdout.write(self.style.SUCCESS('✓ Scheduler parado com sucesso!'))
            
        elif acao == 'status':
            status = AgendadorSincronizacao.obter_status()
            self.stdout.write(self.style.HTTP_INFO('Status do Scheduler:'))
            
            if status['ativo']:
                self.stdout.write(self.style.SUCCESS('  Status: ✓ ATIVO'))
                self.stdout.write(f"\n  Jobs agendados ({len(status['jobs'])}):")
                for job in status['jobs']:
                    self.stdout.write(f"    • {job['nome']}")
                    self.stdout.write(f"      ID: {job['id']}")
                    self.stdout.write(f"      Próxima execução: {job['proxima_execucao']}")
                    self.stdout.write(f"      Intervalo: {job['intervalo']}")
            else:
                self.stdout.write(self.style.WARNING('  Status: ✗ INATIVO'))
            
            # Mostra configuração atual
            self.stdout.write(f"\n  Configurações:")
            self.stdout.write(f"    • URL Base: {SincronizadorAPI.CONFIG['url_base']}")
            self.stdout.write(f"    • Intervalo: {SincronizadorAPI.CONFIG['intervalo_minutos']} minuto(s)")
            self.stdout.write(f"    • Paginações: {len(SincronizadorAPI.CONFIG['paginacoes'])}")
            for pag in SincronizadorAPI.CONFIG['paginacoes']:
                self.stdout.write(f"      - Página {pag['pagina']}, Tamanho {pag['tamanho']}")
            self.stdout.write(f"    • Ativo: {'Sim' if SincronizadorAPI.CONFIG['ativo'] else 'Não'}")
            
        elif acao == 'agora':
            self.stdout.write(self.style.SUCCESS('Executando sincronização manual...'))
            AgendadorSincronizacao.sincronizar_agora()
            self.stdout.write(self.style.SUCCESS('✓ Sincronização concluída!'))
