
from django.core.management.base import BaseCommand
from core.models import Pedido, Etapa, TipoProduto
from django.utils import timezone


class Command(BaseCommand):
    help = 'Cria pedidos de teste para o sistema'

    def handle(self, *args, **kwargs):
        # Buscar a primeira etapa
        primeira_etapa = Etapa.objects.filter(ativa=True).order_by('sequencia').first()
        
        if not primeira_etapa:
            self.stdout.write(self.style.ERROR('Nenhuma etapa encontrada. Execute python manage.py setup_inicial primeiro.'))
            return
        
        # Buscar alguns tipos de produtos para usar nos testes
        tipos_produtos = TipoProduto.objects.all()[:10]
        
        if not tipos_produtos.exists():
            self.stdout.write(self.style.ERROR('Nenhum tipo de produto encontrado. Execute python manage.py setup_inicial primeiro.'))
            return
        
        # Criar pedidos de teste
        pedidos_teste = [
            {
                'nome': 'Farmácia São Paulo',
                'tipo_idx': 0,
                'quantidade': 1000,
                'codigo_pedido': 'FSP-001'
            },
            {
                'nome': 'Drogaria Central',
                'tipo_idx': 1,
                'quantidade': 500,
                'codigo_pedido': 'DC-001'
            },
            {
                'nome': 'Farmácia Rede Vida',
                'tipo_idx': 2,
                'quantidade': 2000,
                'codigo_pedido': 'FRV-001'
            },
            {
                'nome': 'Distribuidora MedMax',
                'tipo_idx': 3,
                'quantidade': 1500,
                'codigo_pedido': 'DMM-001'
            },
            {
                'nome': 'Farmácia Popular',
                'tipo_idx': 0,
                'quantidade': 800,
                'codigo_pedido': 'FP-001'
            },
            {
                'nome': 'Drogaria Nova',
                'tipo_idx': 1,
                'quantidade': 300,
                'codigo_pedido': 'DN-001'
            },
            {
                'nome': 'Farmácia Saúde Total',
                'tipo_idx': 2,
                'quantidade': 1200,
                'codigo_pedido': 'FST-001'
            },
            {
                'nome': 'Rede Farma Mais',
                'tipo_idx': 0,
                'quantidade': 2500,
                'codigo_pedido': 'RFM-001'
            },
            {
                'nome': 'Farmácia do Bairro',
                'tipo_idx': 3,
                'quantidade': 600,
                'codigo_pedido': 'FDB-001'
            },
            {
                'nome': 'Drogaria Express',
                'tipo_idx': 1,
                'quantidade': 400,
                'codigo_pedido': 'DE-001'
            },
        ]
        
        pedidos_criados = 0
        tipos_list = list(tipos_produtos)
        
        for pedido_data in pedidos_teste:
            tipo_produto = tipos_list[pedido_data['tipo_idx'] % len(tipos_list)]
            pedido = Pedido.objects.create(
                nome=pedido_data['nome'],
                tipo=tipo_produto,
                quantidade=pedido_data['quantidade'],
                codigo_pedido=pedido_data['codigo_pedido'],
                etapa_atual=primeira_etapa,
                status='em_fluxo'
            )
            pedidos_criados += 1
            self.stdout.write(self.style.SUCCESS(f'✓ Pedido #{pedido.id} ({pedido.codigo_pedido}) criado: {pedido.nome}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n{pedidos_criados} pedidos de teste criados com sucesso!'))
        self.stdout.write(self.style.WARNING(f'Todos os pedidos estão na etapa "{primeira_etapa.nome}" e disponíveis para serem assumidos.'))
