import re
from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Reidentifica quantidades de cápsulas/envelopes baseado na descrição'
    
    @staticmethod
    def extrair_quantidade_produto(descricao_web):
        """
        Extrai a quantidade de unidades do produto APENAS de CAPSULA e ENVELOPE
        Busca pelos padrões: "CAPSULA: XXcap" ou "ENVELOPE: XXenv"
        Retorna: int ou None se não encontrar
        """
        if not descricao_web:
            return None
        
        descricao_upper = descricao_web.upper()
        
        # Padrão 1: "CAPSULA: XXcap" (apenas após a palavra CAPSULA:)
        match = re.search(r'CAPSULA\s*:\s*(\d+)\s*CAP', descricao_upper)
        if match:
            try:
                quantidade = int(match.group(1))
                return quantidade if quantidade > 0 else None
            except (ValueError, AttributeError):
                return None
        
        # Padrão 2: "ENVELOPE: XXenv" (apenas após a palavra ENVELOPE:)
        match = re.search(r'ENVELOPE\s*:\s*(\d+)\s*ENV', descricao_upper)
        if match:
            try:
                quantidade = int(match.group(1))
                return quantidade if quantidade > 0 else None
            except (ValueError, AttributeError):
                return None
        
        return None
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando reidentificação de quantidades...'))
        
        pedidos = Pedido.objects.all()
        atualizados = 0
        nao_alterados = 0
        
        for pedido in pedidos:
            nova_quantidade = self.extrair_quantidade_produto(pedido.descricao_web)
            
            if nova_quantidade is not None:
                if pedido.quantidade != nova_quantidade:
                    self.stdout.write(
                        f'Pedido {pedido.id_api}: {pedido.quantidade} -> {nova_quantidade} '
                        f'({pedido.descricao_web[:80]}...)'
                    )
                    pedido.quantidade = nova_quantidade
                    pedido.save()
                    atualizados += 1
                else:
                    nao_alterados += 1
            else:
                nao_alterados += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Reidentificação concluída!\n'
                f'  Atualizados: {atualizados}\n'
                f'  Não alterados: {nao_alterados}\n'
                f'  Total: {atualizados + nao_alterados}'
            )
        )
