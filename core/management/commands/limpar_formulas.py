"""
Comando para limpar dados do novo fluxo (PedidoMestre, FormulaItem)
Útil para resetar o banco de dados e sincronizar do zero
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import PedidoMestre, FormulaItem, HistoricoEtapaFormula, ChecklistExecucaoFormula
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpa todos os dados do novo fluxo (PedidoMestre, FormulaItem, HistoricoEtapaFormula, ChecklistExecucaoFormula)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a exclusão (sem isso, apenas mostra o que seria deletado)',
        )

    def handle(self, *args, **options):
        confirmar = options.get('confirmar', False)

        # Contar registros
        total_formulas = FormulaItem.objects.count()
        total_pedidos_mestres = PedidoMestre.objects.count()
        total_historicos = HistoricoEtapaFormula.objects.count()
        total_checklists = ChecklistExecucaoFormula.objects.count()

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('LIMPEZA DOS DADOS DO NOVO FLUXO'))
        self.stdout.write(self.style.WARNING('=' * 70))

        self.stdout.write(f'\nDados a serem deletados:')
        self.stdout.write(f'  - PedidoMestre: {total_pedidos_mestres}')
        self.stdout.write(f'  - FormulaItem: {total_formulas}')
        self.stdout.write(f'  - HistoricoEtapaFormula: {total_historicos}')
        self.stdout.write(f'  - ChecklistExecucaoFormula: {total_checklists}')

        self.stdout.write(f'\nTOTAL DE REGISTROS: {total_pedidos_mestres + total_formulas + total_historicos + total_checklists}')

        if not confirmar:
            self.stdout.write(self.style.WARNING(
                '\n[!] Para confirmar e deletar os dados, use: python manage.py limpar_formulas --confirmar'
            ))
            return

        # Confirmar deleção
        self.stdout.write(self.style.WARNING(
            '\n⚠️  DELETANDO TODOS OS DADOS DO NOVO FLUXO...'
        ))

        try:
            with transaction.atomic():
                # Deletar em ordem de dependência (FK relationships)
                ChecklistExecucaoFormula.objects.all().delete()
                self.stdout.write(f'[OK] Deletados {total_checklists} ChecklistExecucaoFormula')

                HistoricoEtapaFormula.objects.all().delete()
                self.stdout.write(f'[OK] Deletados {total_historicos} HistoricoEtapaFormula')

                FormulaItem.objects.all().delete()
                self.stdout.write(f'[OK] Deletados {total_formulas} FormulaItem')

                PedidoMestre.objects.all().delete()
                self.stdout.write(f'[OK] Deletados {total_pedidos_mestres} PedidoMestre')

            self.stdout.write(self.style.SUCCESS('\n✅ LIMPEZA CONCLUÍDA COM SUCESSO!'))
            self.stdout.write(self.style.SUCCESS('Você pode agora rodar a sincronização: python manage.py sincronizar_formulas_api'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERRO AO LIMPAR: {str(e)}'))
            logger.error(f'Erro ao limpar dados: {str(e)}')
