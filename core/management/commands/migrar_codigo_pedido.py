from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Atualiza código_pedido para o novo formato com IDs da API'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n🔄 Atualizando formato de código_pedido...\n'))
        
        pedidos = Pedido.objects.filter(id_api__isnull=False).order_by('-id_api')
        total = pedidos.count()
        atualizados = 0
        
        for pedido in pedidos:
            novo_codigo = f"API-{pedido.id_api}-{pedido.id_pedido_api}-{pedido.id_pedido_web}"
            
            if pedido.codigo_pedido != novo_codigo:
                self.stdout.write(f"ID {pedido.id_api}: {pedido.codigo_pedido} → {novo_codigo}")
                pedido.codigo_pedido = novo_codigo
                pedido.save()
                atualizados += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Atualização concluída!'))
        self.stdout.write(f'   📝 Atualizados: {atualizados}')
        self.stdout.write(f'   📊 Total de pedidos: {total}\n')
