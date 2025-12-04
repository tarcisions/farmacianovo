import re
from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Re-identifica as quantidades de produtos a partir das descrições'
    
    @staticmethod
    def extrair_quantidade_produto(descricao_web):
        """
        Extrai a quantidade de unidades do produto (cápsulas, sachês, etc) da descrição
        Exemplos: "30CAP" -> 30, "90CAP" -> 90, "60 SACHE" -> 60
        Retorna: int ou None se não encontrar
        """
        if not descricao_web:
            return None
        
        descricao_upper = descricao_web.upper()
        
        # Padrões para encontrar quantidade
        # Busca por números seguidos de CAP, SACHE, etc
        padrao_quantidade = r'(\d+)\s*(CAP|CÁP|CAPSULA|SACHE|SACHÊ|ENVELOPE|DOSE|FRASCO|ML)'
        
        match = re.search(padrao_quantidade, descricao_upper)
        if match:
            try:
                quantidade = int(match.group(1))
                return quantidade if quantidade > 0 else None
            except (ValueError, AttributeError):
                return None
        
        return None
    
    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Re-identificando quantidades de produtos...")
        
        pedidos = Pedido.objects.all()
        total = pedidos.count()
        atualizados = 0
        
        for idx, pedido in enumerate(pedidos, 1):
            try:
                quantidade_extraida = self.extrair_quantidade_produto(pedido.descricao_web)
                
                if quantidade_extraida and quantidade_extraida != pedido.quantidade:
                    self.stdout.write(
                        f"[{idx}/{total}] Pedido {pedido.id_api}: "
                        f"quantidade alterada de {pedido.quantidade} para {quantidade_extraida} "
                        f"({pedido.tipo_identificado})"
                    )
                    pedido.quantidade = quantidade_extraida
                    pedido.save()
                    atualizados += 1
                elif idx % 50 == 0:
                    self.stdout.write(f"[{idx}/{total}] Processado...")
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao processar pedido {pedido.id_api}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Re-identificação concluída!"))
        self.stdout.write(f"   📝 Total de pedidos processados: {total}")
        self.stdout.write(f"   🔄 Atualizados: {atualizados}")
