from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Lista pedidos que necessitam ajuste manual (tipo desconhecido)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=20,
            help='Limite de pedidos a exibir'
        )
    
    def handle(self, *args, **kwargs):
        limite = kwargs.get('limite', 20)
        
        # Buscar pedidos com tipo desconhecido
        pedidos_desconhecidos = Pedido.objects.filter(
            tipo_identificado='desconhecido'
        ).order_by('-criado_em')[:limite]
        
        if not pedidos_desconhecidos.exists():
            self.stdout.write(self.style.SUCCESS('✅ Todos os pedidos têm tipo identificado!'))
            return
        
        total = Pedido.objects.filter(tipo_identificado='desconhecido').count()
        
        self.stdout.write(self.style.WARNING(f'\n⚠️  {total} pedido(s) precisam de ajuste manual'))
        self.stdout.write(f'Mostrando os primeiros {limite}:\n')
        
        self.stdout.write('-' * 150)
        self.stdout.write(f"{'ID':<8} {'Código':<25} {'Descrição':<80} {'Quantidade':<12} {'Data API':<15}")
        self.stdout.write('-' * 150)
        
        for pedido in pedidos_desconhecidos:
            descricao = pedido.descricao_web[:75] if pedido.descricao_web else 'N/A'
            data = pedido.data_atualizacao_api or 'N/A'
            id_api = str(pedido.id_api) if pedido.id_api else 'N/A'
            self.stdout.write(
                f"{id_api:<8} {pedido.codigo_pedido:<25} {descricao:<80} {pedido.quantidade:<12} {str(data):<15}"
            )
        
        self.stdout.write('-' * 150)
        self.stdout.write(self.style.WARNING(f'\n💡 Dica: Acesse o admin ou frontend para atualizar o "Tipo" desses pedidos\n'))
