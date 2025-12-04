"""
Comando para limpar/resetar a tabela de pedidos
Uso: python manage.py limpar_pedidos
"""

from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Limpa todos os pedidos da tabela'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a limpeza sem pedir confirmação'
        )
    
    def handle(self, *args, **options):
        total = Pedido.objects.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('Nenhum pedido para limpar'))
            return
        
        self.stdout.write(self.style.WARNING(f'Aviso: Você vai deletar {total} pedido(s)!'))
        
        if not options['confirmar']:
            confirmar = input('Tem certeza? Digite "SIM" para confirmar: ')
            if confirmar.upper() != 'SIM':
                self.stdout.write(self.style.ERROR('Operação cancelada'))
                return
        
        Pedido.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Sucesso! {total} pedido(s) deletado(s)')
        )
