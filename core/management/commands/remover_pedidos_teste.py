from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Remove todos os pedidos de teste do sistema'

    def handle(self, *args, **kwargs):
        # Códigos dos pedidos de teste que serão removidos
        codigos_teste = [
            'FSP-001', 'DC-001', 'FRV-001', 'DMM-001', 'FP-001',
            'DN-001', 'FST-001', 'RFM-001', 'FDB-001', 'DE-001'
        ]
        
        # Contar quantos pedidos serão removidos
        pedidos_para_remover = Pedido.objects.filter(codigo_pedido__in=codigos_teste)
        quantidade = pedidos_para_remover.count()
        
        if quantidade == 0:
            self.stdout.write(self.style.WARNING('Nenhum pedido de teste encontrado para remover.'))
            return
        
        # Remover os pedidos
        pedidos_para_remover.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {quantidade} pedido(s) de teste removido(s) com sucesso!')
        )
