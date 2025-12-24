from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    HistoricoEtapa, HistoricoControleQualidade, 
    PontuacaoFuncionario, RegistroExpedicao
)
from core.models import Pedido


class Command(BaseCommand):
    help = 'Limpa todos os dados de um funcionário (Histórico de Etapas, CQ, Pontuação, etc)'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username do funcionário a ser limpo'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            funcionario = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Funcionário "{username}" não encontrado!')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'\n⚠️  Você está prestes a limpar TODOS os dados de: {funcionario.get_full_name()} ({username})\n')
        )
        
        confirmacao = input('Digite "SIM" para confirmar: ')
        
        if confirmacao.upper() != 'SIM':
            self.stdout.write(self.style.ERROR('❌ Operação cancelada!'))
            return

        # Contar registros antes de deletar
        count_etapas = HistoricoEtapa.objects.filter(funcionario=funcionario).count()
        count_cq = HistoricoControleQualidade.objects.filter(funcionario=funcionario).count()
        count_pontuacao = PontuacaoFuncionario.objects.filter(funcionario=funcionario).count()
        count_expedicao = RegistroExpedicao.objects.filter(funcionario=funcionario).count()
        
        # Pedidos assumidos por ele
        pedidos_assumidos = Pedido.objects.filter(funcionario_na_etapa=funcionario)
        count_pedidos = pedidos_assumidos.count()

        self.stdout.write(f'\n📊 Registros a serem deletados:')
        self.stdout.write(f'  - Histórico de Etapas: {count_etapas}')
        self.stdout.write(f'  - Formulários de CQ: {count_cq}')
        self.stdout.write(f'  - Pontuação: {count_pontuacao}')
        self.stdout.write(f'  - Expedições: {count_expedicao}')
        self.stdout.write(f'  - Pedidos Assumidos: {count_pedidos}')
        
        # Limpar tudo
        HistoricoEtapa.objects.filter(funcionario=funcionario).delete()
        HistoricoControleQualidade.objects.filter(funcionario=funcionario).delete()
        PontuacaoFuncionario.objects.filter(funcionario=funcionario).delete()
        RegistroExpedicao.objects.filter(funcionario=funcionario).delete()
        
        # Desassociar pedidos
        pedidos_assumidos.update(funcionario_na_etapa=None)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Funcionário "{username}" foi resetado com sucesso!\n')
        )
