"""
Comando para limpar executações de checklists inconsistentes.
Remove execuções de checklists desativados e sincroniza os dados.
"""

from django.core.management.base import BaseCommand
from core.models import ChecklistExecucaoFormula, HistoricoEtapaFormula, Checklist


class Command(BaseCommand):
    help = 'Limpa execuções de checklists desativados e sincroniza dados inconsistentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a limpeza sem fazer alterações',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Iniciando limpeza de checklists inconsistentes...'))
        
        # 1. Remover execuções de checklists desativados
        self.stdout.write('\n1. Procurando execuções de checklists desativados...')
        
        execucoes_desativadas = ChecklistExecucaoFormula.objects.filter(
            checklist__ativo=False
        )
        
        total_desativadas = execucoes_desativadas.count()
        
        if total_desativadas > 0:
            self.stdout.write(
                self.style.WARNING(f'   Encontradas {total_desativadas} execuções de checklists desativados')
            )
            if not dry_run:
                execucoes_desativadas.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'   ✓ Deletadas {total_desativadas} execuções')
                )
            else:
                self.stdout.write('   [DRY-RUN] Não foram deletadas (use sem --dry-run para executar)')
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ Nenhuma execução de checklist desativado encontrada'))
        
        # 2. Sincronizar execuções com checklists ativos por historico
        self.stdout.write('\n2. Sincronizando execuções de checklists ativos...')
        
        historicos = HistoricoEtapaFormula.objects.all()
        total_sincronizadas = 0
        total_criadas = 0
        total_atualizadas = 0
        
        for historico in historicos:
            # Buscar checklists ativos da etapa
            checklists_ativos = Checklist.objects.filter(
                etapa=historico.etapa,
                ativo=True
            )
            
            # Criar execuções para checklists ativos que não têm execução
            for checklist in checklists_ativos:
                execucao, created = ChecklistExecucaoFormula.objects.get_or_create(
                    historico_etapa=historico,
                    checklist=checklist,
                    defaults={'marcado': False, 'pontos_gerados': checklist.pontos_do_check}
                )
                
                if created:
                    total_criadas += 1
                elif execucao.pontos_gerados != checklist.pontos_do_check:
                    # Atualizar pontos se foram editados
                    if not dry_run:
                        execucao.pontos_gerados = checklist.pontos_do_check
                        execucao.save()
                    total_atualizadas += 1
            
            # Remover execuções de checklists desativados/deletados
            execucoes_para_remover = ChecklistExecucaoFormula.objects.filter(
                historico_etapa=historico
            ).exclude(
                checklist__in=checklists_ativos
            )
            
            total_para_remover = execucoes_para_remover.count()
            
            if total_para_remover > 0:
                if not dry_run:
                    execucoes_para_remover.delete()
            
            total_sincronizadas += total_para_remover
        
        self.stdout.write(
            self.style.SUCCESS(
                f'   ✓ Sincronização completa:\n'
                f'      - Criadas: {total_criadas}\n'
                f'      - Atualizadas: {total_atualizadas}\n'
                f'      - Removidas: {total_sincronizadas}'
            )
        )
        
        # 3. Resumo
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Limpeza concluída! Total de alterações: '
                f'{total_desativadas + total_criadas + total_atualizadas + total_sincronizadas}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ Modo DRY-RUN ativo: nenhuma alteração foi feita.\n'
                    'Execute sem --dry-run para aplicar as alterações.'
                )
            )
